
# Controla todos los juegos activos que hay actualmente y se encarga de anunciar
# a los jugadores que estan esperando que ha iniciado la partida

from fastapi import WebSocket
from routers.partidas import *
from funcionesAuxiliaresPartida import *
from typing import Literal
from routers.juego import *
import random

# Crea una nueva sesion de juego. Nunca se llama directamente a esta sino a GameConnectionManager
# el cual se encargara de que si no existe crear uno nuevo

class GameSession:
        def __init__(self, game_id: int):
            self.game_id = game_id
            self.players: dict[str, WebSocket] = {}
            self.status = "WAITING"
            self.board_state = {}
            self.dados: dict[Literal["izq", "der"], list[int]] = {"izq": [], "der": []}
            self.players_en_fin_ronda = 0       # Jugadores que han acabado la ronda
        
        @property
        def is_full(self):
            return len(self.players) == 4
        
        async def broadcast (self, message: dict):
            jugadores_desconectados = []

            for player_id, ws in self.players.items():
                if ws is not None:
                    try:
                        await ws.send_json(message)
                    except Exception as e:
                        # Si falla el envío (ej. WebSocketDisconnect), capturamos el error
                        print(f"Omitiendo jugador {player_id} (desconectado): {e}")
                        jugadores_desconectados.append(player_id)
            
            # Limpiamos a los "fantasmas" marcando su socket como None
            for p_id in jugadores_desconectados:
                self.players[p_id] = None

class GameManager:
    def __init__(self):
        self.active_games: dict[int, GameSession] = {}

    async def connect(self, websocket: WebSocket, game_id: int, player_id: str):
        await websocket.accept()

        # Crear el nuevo game en caso de que no exita

        if game_id not in self.active_games:
            self.active_games[game_id] = GameSession(game_id)
        
        session = self.active_games[game_id]

        reconnect = player_id in session.players

        # Verificar que el usuario no esta conectado desde otro dispositvo

        if reconnect:
            old_socket = session.players[player_id]
            if old_socket is not None:
                try:
                    await old_socket.send_json({
                        "type": "force_disconnect",
                        "message": "Nueva conexion desde otro dispositivo"
                    })
                    await old_socket.close()
                except:
                    pass

        # Verficar que la partida no esta llena

        if not reconnect and (session.is_full or session.status != "WAITING"):
            await websocket.send_json({"error": "La partida esta llena"})
            await websocket.close()
            return False

        session.players[player_id] = websocket
        
        if "positions" not in session.board_state:
            session.board_state["positions"] = {}
            session.board_state["balances"] = {}
            session.board_state["characters"] = {}
            session.board_state["turns"] = {}
            session.board_state["order"] = {}
            
        if player_id not in session.board_state["positions"]:
                    session.board_state["positions"][player_id] = 1
                    session.board_state["balances"][player_id] = 1
                    session.board_state["turns"][player_id] = 1
                    session.board_state["order"][player_id] = len(session.players)

        # Asignarle la casilla inicial (ej. la casilla 1)
        if reconnect:
            # Le avisamos al jugador que ha vuelto con éxito y el estado actual
            await websocket.send_json({
                "type": "reconnect_success",
                "game_status": session.status,
                "current_board": session.board_state
            })
        else:
            # Lógica normal para nuevos jugadores
            await session.broadcast({
                "type" : "lobby_update",
                "players_connected": len([p for p in session.players.values() if p is not None]),
                "message": f"Jugador {player_id} se ha unido"
            })

            if session.is_full:
                session.status = "PLAYING"
                await session.broadcast({
                    "type": "game_start",
                    "message": "Empieza el juego"
                })

                # Sorteamos los dados de la primera ronda para que sean iguales y se lancen por orden de unión a la partida
                for _ in range(4):
                    dadoizq, dadoder, _ = tirarDados(4) # Posición 4 para que en la primera ronda todos partan igual

                    session.dados["izq"].append(dadoizq)
                    session.dados["der"].append(dadoder)

        return True

    async def disconnect(self, websocket: WebSocket, game_id: int, player_id: str):
        if game_id in self.active_games:
            session = self.active_games[game_id]
            
            if player_id in session.players:
                
                if session.status == "WAITING":

                    # obtener el orden del jugador desconectado
                    disconnected_order = session.board_state["order"][player_id]

                    # eliminar jugador
                    del session.players[player_id]
                    del session.board_state["order"][player_id]
                    del session.board_state["positions"][player_id]
                    del session.board_state["balances"][player_id]

                    # reajustar turnos
                    for p_id, order in session.board_state["order"].items():    # Para obtener clave y valor
                        if order > disconnected_order:
                            session.board_state["order"][p_id] -= 1

    async def process_action(self, game_id: int, user: str, action: str, payload: dict = None):
        session = self.active_games[game_id]
        
        match action:
            case "select_player":

                character = payload["character"]

                # Vigilamos que le toque elegir al usuario
                num_personajes = len(session.board_state["characters"])    # Personajes ya elegidos

                if (num_personajes + 1) != session.board_state["order"][user]:     # Si no le toca elegir mandamos error

                    await session.players[user].send_json({"error": "No es tu turno de elección"})   # JSON a su ws
                
                elif character in session.board_state["characters"].values():   # Si el personaje ya se ha elegido

                    await session.players[user].send_json({"error": "Personaje ya elegido"})

                else:
                    session.board_state["characters"][user] = character 
                    await session.broadcast({
                        "type": "player_selected",
                        "user": user,
                        "character": character
                    })

                    if num_personajes + 1 == 4:         # Fin de elecciones -> Inicio de partida real
                        await session.broadcast({
                            "type": "all_players_selected",
                            "message": "Fin de elección de personajes"
                        })

            case "move_player":

                orden = session.board_state["order"].get(user)

                if orden is None:
                    return

                dado1 = session.dados["izq"][orden - 1]
                dado2 = session.dados["der"][orden - 1]

                nueva_casilla = session.board_state["positions"].get(user) + dado1 + dado2
                session.board_state["positions"][user] = nueva_casilla

                actualizar_casilla(game_id, user, nueva_casilla)

                await session.broadcast({
                    "type": "player_moved",
                    "user": user,
                    "dado1": dado1,
                    "dado2": dado2,
                    "nueva_casilla": nueva_casilla
                })
            
            case "end_round":
                session.players_en_fin_ronda += 1

                # Si los 4 han acabado la ronda lanzar dados y avisar al visionario
                if session.players_en_fin_ronda == 4:
                    session.players_en_fin_ronda = 0
                    
                    session.dados["izq"] = []
                    session.dados["der"] = []
                    sumas = []
                    for i in range(4):

                        dadoizq, dadoder, _ = tirarDados(i + 1)  # hacer 4 tiradas y guardarlas
                        session.dados["izq"].append(dadoizq)
                        session.dados["der"].append(dadoder)
                        sumas.append(dadoizq + dadoder)

                    # Avisamos al visionario
                    for p_id, personaje in session.board_state["characters"].items():
                        if personaje == "Vidente":
                            await session.players.get(p_id).send_json({
                                "type": "dice_shown",
                                "punt": sumas
                            })
                        
                        if personaje == 'Videojugador':
                            minijuegos = listar_minijuegos()
                            dos_juegos = random.sample(minijuegos, 2)

                            # Creamos un diccionario con los minijuegos elegidos 
                            resultado = [MinijuegoInfo(nombre=juego[0], descripcion=juego[1]).model_dump() for juego in dos_juegos]

                            await session.players.get(p_id).send_json({
                                "type": "choose_minijuego",
                                "minijuegos": resultado
                            })
                    
                    #session.board_state["turn"][player_id] ++ LO INCREMENTAMOS AQUI O CON LA RESPUESTA DEL VIDENTE
                    #FALLA: SE PUEDE TIRAR DADOS SIN QUE SEA TU TURNO
                    #FALLA: AL DARLE A TERMINAR PARTIDA LOS 4, NO AVISA AL VIDENTE CON LOS DADOS
                    # OBSERVACIÓN: avisar al vidente siempre?? 
                
            case "ini_round":
                if session.board_state["characters"].get(user) == 'Videojugador':   # Si el user es el videojugador, iniciamos minijuego
                    minijuego = payload["minijuego"]
                    descripcion = payload["descripcion"]
                    
                    await session.broadcast({
                        "type": "ini_minijuego",
                        "minijuego": minijuego,
                        "descripcion": descripcion,
                        "estado_partida": session.board_state
                    })


manager = GameManager()