
# Controla todos los juegos activos que hay actualmente y se encarga de anunciar
# a los jugadores que estan esperando que ha iniciado la partida

from fastapi import WebSocket
from routers.partidas import *

# Crea una nueva sesion de juego. Nunca se llama directamente a esta sino a GameConnectionManager
# el cual se encargara de que si no existe crear uno nuevo

class GameSession:
        def __init__(self, game_id: int):
            self.game_id = game_id
            self.players: dict[str, WebSocket] = {}
            self.status = "WAITING"
            self.board_state = {}
        
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
            
        if player_id not in session.board_state["positions"]:
                    session.board_state["positions"][player_id] = 1
                    session.board_state["balances"][player_id] = 1
                    session.board_state["turns"] = len



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

        return True

    async def disconnect(self, websocket: WebSocket, game_id: int, player_id:str):
        if game_id in self.active_games:
            session = self.active_games[game_id]
            if player_id in session.players:

                session.players[player_id] = None
                await session.broadcast({
                    "type": "player_disconnected",
                    "message": "El jugador"
                })

    async def process_action(self, game_id: int, user: str, action: str, payload: dict = None):
        session = self.active_games[game_id]
        
        match action:
            case "select_player":

                character = payload[user]
                session.board_state[characters][user] = character 
                await session.broadcast({
                    "type": "player_selected",
                    "user": user,
                    "character": character
                })

            case "move_player":
                
                dado = tirarDado(pos)
                nueva_casilla = session.board_state["posiciones"][user] + dado
                session.board_state["posiciones"][user] = nueva_casilla

                actualizar_casilla(game_id, user, nueva_casilla)

                await session.broadcast({
                    "type": "player_moved",
                    "user": user,
                    "result": dado,
                    "nueva_casilla": nueva_casilla
                })
                
    
manager = GameManager()