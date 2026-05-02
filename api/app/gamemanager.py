
# Controla todos los juegos activos que hay actualmente y se encarga de anunciar
# a los jugadores que estan esperando que ha iniciado la partida

from fastapi import WebSocket
#from requests import session
# Si no comento esto no va
# from requests import session
from routers.partidas import *
from routers.juego import *
from funcionesAuxiliaresPartida import *
from typing import Literal
from routers.juego import *
import random
import asyncio
from logicaMinijuegos import *

MAX_JUGADORES = 4
META = 71

# Crea una nueva sesion de juego. Nunca se llama directamente a esta sino a GameConnectionManager
# el cual se encargara de que si no existe crear uno nuevo

class GameSession:
        def __init__(self, game_id: int):
            self.game_id = game_id
            self.players: dict[str, WebSocket] = {}
            self.status = "WAITING"
            self.board_state = {}
            self.dados: dict[Literal["izq", "der"], list[int]] = {"izq": [], "der": []}
            self.players_id = []
            # Minijuegos
            self.minijuego_actual = None
            self.minijuego_tipo = None  # "orden" o "casilla" 
            self.minijuego_detalles = {} # {"objetivo": 10, "cartas": [3, 15, 27, 40], ...} solo para elección de orden
            self.minijuego_scores = {}   # {"Edu1": 350, "Edu2": 410..., "Edu4": 290}
            self.minijuego_participantes = [] # Para gestionar los ids que participan en el minijuego actual
            self.poker_fase = None
            self.poker_bote = 0
            self.poker_activos = [] # Jugadores que no se han retirado
            self.poker_respuestas_fase = {} # Lo que ha hecho cada uno en la ronda actual
            self.poker_apuesta_actual = 0 # Apuesta más alta de la fase actual
            self.poker_apuestas_acumuladas = {} # Total apostado por cada jugador en la fase actual

            self.avance_extra = 0 # Para gestionar el avance extra que da el objeto de avanzar casillas en el mismo turno
            self.penalizacion_pendiente = {} # Para gestionar objetos Barrera que se usan en el mismo turno

        @property
        def is_full(self):
            return len(self.players) == MAX_JUGADORES
        
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

        # Crear el nuevo game en caso de que no exista y se encuentre en la BD, si no existe no se permitirá la conexión
        if not existe_partida(game_id):
            await websocket.send_json({"error": "La partida no existe"})
            await websocket.close()
            return False

        elif game_id not in self.active_games:  # Se ha conectado el primer jugador por lo que creamos la sesión de juego
            self.active_games[game_id] = GameSession(game_id)
        
        # Verificamos que el usuario este asociado a la partida en la BD
        if not jugador_en_partida(player_id, game_id):
            await websocket.send_json({"error": "No estás asociado a esta partida"})
            await websocket.close()
            return False

        session = self.active_games[game_id]

        session.players_id.append(player_id)

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

        # Verficar que la partida no esta llena ni empezada

        if not reconnect and (session.is_full or session.status != "WAITING"):
            eliminar_jugador_partida(player_id, game_id) # Eliminamos al jugador de la partida en la BD para que no haya problemas
            await websocket.send_json({"error": "La partida esta llena"})
            await websocket.close()
            return False

        session.players[player_id] = websocket
        session.penalizacion_pendiente[player_id] = 0 # Inicializamos la penalización pendiente a 0 para el jugador que se conecta

        #Cuando se une el primer jugador
        if "positions" not in session.board_state:
            session.board_state["positions"] = {} # Casilla en la que está cada jugador
            session.board_state["balances"] = {} # Dinero que le queda a cada jugador
            session.board_state["characters"] = {} # Personaje para cada jugador
            session.board_state["round"] = 1 # Ronda en la que nos encontramos
            session.board_state["order"] = {} # Orden de tirada para cada ronda
            session.board_state["penalty_turns"] = {} # Turnos de penalización que le quedan a cada jugador por caer en casillas de barrera
            session.board_state["turn"] = 1     # guarda el turno en el que nos encontramos en la ronda
            
        if player_id not in session.board_state["positions"]:
                    session.board_state["positions"][player_id] = 0 # Todos los jugadores empiezan en la casilla 0
                    session.board_state["balances"][player_id] = 1
                    session.board_state["order"][player_id] = len(session.players)
                    session.board_state["penalty_turns"][player_id] = 0 # Inicializado a 0

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
                "players_connected": [p for p in session.players.keys()],
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
            
            # Comprobamos que el jugador existe y que el websocket que se ha desconectado es el último que se ha registrado
            if player_id in session.players and session.players.get(player_id) == websocket:
                
                if session.status == "WAITING":

                    # obtener el orden del jugador desconectado
                    disconnected_order = session.board_state["order"][player_id]

                    # eliminar jugador
                    del session.players[player_id]
                    del session.board_state["order"][player_id]
                    del session.board_state["positions"][player_id]
                    del session.board_state["balances"][player_id]
                    del session.board_state["turns"][player_id]
                    del session.board_state["penalty_turns"][player_id]
                    del session.penalizacion_pendiente[player_id]
                    
                    eliminar_jugador_partida(player_id, game_id) # Eliminamos al jugador de la partida en la BD

                    # reajustar turnos
                    for p_id, order in session.board_state["order"].items():    # Para obtener clave y valor
                        if order > disconnected_order:
                            session.board_state["order"][p_id] -= 1

                    await session.broadcast({
                        "type": "player_disconnected",
                        "players_connected": [p for p in session.players.keys()],
                        "message": f"Jugador {player_id} se ha desconectado"
                    })

                elif session.status == "PLAYING":
                    # Marcamos como desconectado para que no reciba mensajes
                    session.players[player_id] = None

                    await session.broadcast({
                        "type": "not_playing",
                        "player": player_id
                    })

                elif session.status == "ENDING":
                    del session.players[player_id]  # Eliminamos al jugador desconectado
                    eliminar_jugador_partida(player_id, game_id) # Eliminamos al jugador de la partida en la BD

                    if len(session.players) == 0:
                        del self.active_games[game_id]  # Si no queda nadie eliminamos la partida
                        # No hace falta eliminar la partida porque si no tiene jugadores asociados se eliminará gracias al trigger
                        return

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

                    if num_personajes + 1 == MAX_JUGADORES:         # Fin de elecciones -> Inicio de partida real
                        await session.broadcast({
                            "type": "all_players_selected",
                            "message": "Fin de elección de personajes"
                        })

            case "move_player":
                # Obtenemos el orden del jugador para esta ronda
                orden = session.board_state["order"].get(user)

                if orden is None:
                    return

                # Comprobamos que no tenga penalización activa
                if session.board_state["penalty_turns"].get(user, 0) > 0:
                    await session.players[user].send_json({
                        "error": f"Tienes {session.board_state['penalty_turns'][user]} turnos de penalización restantes. No puedes tirar los dados."
                    })
                    return

                # A quién le toca tirar ahora
                turno_actual = session.players_en_fin_ronda + 1

                if orden != turno_actual:
                    await session.players[user].send_json({
                        "error": f"No es tu turno. Le toca al jugador {turno_actual}"
                    })
                    return

                dado1 = session.dados["izq"][orden - 1]
                dado2 = session.dados["der"][orden - 1]

                nueva_casilla = session.board_state["positions"].get(user) + dado1 + dado2 + session.avance_extra
                
                if nueva_casilla > META:
                    nueva_casilla = META
                        
                session.board_state["positions"][user] = nueva_casilla

                actualizar_casilla(game_id, user, nueva_casilla)
                
                session.ha_movido_en_turno = True
                await session.broadcast({
                    "type": "player_moved",
                    "user": user,
                    "dado1": dado1,
                    "dado2": dado2,
                    "nueva_casilla": nueva_casilla
                })

                tipo_casilla,extra = obtenerTipoCasilla(nueva_casilla)
                
                await session.broadcast({
                    "type": "tipo_casilla",
                    "casilla": tipo_casilla,
                    "extra": extra
                })

                # PUEDE IR ARRIBA Y EVITARNOS UN MENSAJE???
                if extra == "final":
                    await session.broadcast({
                        "type": "fin_partida",
                        "winner": user
                    })
                    session.status = "ENDING"    # Cambiamos el estado de la partida para aceptar desconexiones de nuevo
                    # Las conexiones deberán ser cerradas por los jugadores para poder limpiar la partida de memoria
                    return
                
                if tipo_casilla == 'mov': 
                    # Escapista solo se reduce en una casilla si es negativa
                    if session.board_state["characters"].get(user) == "Escapista" and extra < 0: 
                        extra += 1
                    
                    nueva_casilla = session.board_state["positions"].get(user) + extra
                    session.board_state["positions"][user] = nueva_casilla
                    actualizar_casilla(game_id, user, nueva_casilla)
                    await session.broadcast({
                        "type": "player_moved",
                        "user": user,
                        "nueva_casilla": nueva_casilla
                    })

                if tipo_casilla == 'mini':
                    # Tenemos que avisar al frontend del minijuego que ha caído
                    await session.broadcast({
                        "type": "minijuego_casilla",
                        "user": user,
                        "minijuego": extra,
                        "descripcion": obtener_descripcion_minijuego_casilla(extra)
                    })

                    # Distintas acciones para cada minijuego
                    if extra == 'Dilema del Prisionero':
                        # Verificar si hay otro jugador en la misma casilla
                        jugadores_en_casilla = [p_id for p_id, pos in session.board_state["positions"].items() if pos == nueva_casilla]
                        if len(jugadores_en_casilla) == 2:  # Solo si hay exactamente dos jugadores (1vs1)
                            for p_id in jugadores_en_casilla:
                                await session.players[p_id].send_json({
                                    "type": "ini_minijuego",
                                    "minijuego": extra,
                                    "descripcion": obtener_descripcion_minijuego_casilla(extra)
                                })
                        session.minijuego_actual = extra
                        session.minijuego_tipo = "casilla"
                        session.minijuego_participantes = jugadores_en_casilla
                    
                    elif extra == "Doble o Nada":
                        session.minijuego_actual = extra
                        session.minijuego_tipo = "casilla"
                        session.minijuego_participantes = [user]    # Solo el jugador que ha caído en la casilla participa
                        await session.players[user].send_json({
                            "type": "ini_minijuego",
                            "minijuego": extra,
                            "descripcion": obtener_descripcion_minijuego_casilla(extra)
                        })
                    elif extra == "Mano de Poker":
                        session.minijuego_actual = extra
                        session.minijuego_tipo = "casilla"
                        # Participan los jugadores que tengan al menos 1 moneda para apostar
                        session.minijuego_participantes = [p_id for p_id, saldo in session.board_state["balances"].items() if saldo > 0]

                        if len(session.minijuego_participantes) < 2:
                            # Cancelar si no hay suficientes
                            await session.broadcast({
                                "type": "info", 
                                "message": "No hay suficientes jugadores con saldo para jugar al póker."
                            })
                            session.minijuego_actual = None
                            session.minijuego_participantes = []
                        else:
                            # Pedimos a cada participante que haga su apuesta 
                            for p_id in session.minijuego_participantes:
                                await session.players[p_id].send_json({
                                    "type": "ini_minijuego",
                                    "minijuego": extra,
                                    "descripcion": "Haz tu apuesta"
                                })
                            await iniciar_poker_real(session)

                if tipo_casilla == 'obj':
                    # Tenemos que avisar al frontend del objeto que ha caído
                    if extra == '1':   # Sorteo de efecto de ruleta
                        premios = ["+3 Casillas","-3 Casillas","+3 Monedas","-3 Monedas"]
                        premio = random.choice(premios)
                        
                        await session.broadcast({
                            "type": "obtener_objeto",
                            "user": user,
                            "objeto": premio,
                            "descripcion": f"Has obtenido: {premio}"
                        })

                        # Aplicar el efecto inmediatamente
                        if premio == "+3 Casillas":
                            nueva_pos = min(session.board_state["positions"][user] + 3, META)
                            session.board_state["positions"][user] = nueva_pos
                            actualizar_casilla(game_id, user, nueva_pos)
                            await session.broadcast({
                                "type": "player_moved",
                                "user": user,
                                "nueva_casilla": nueva_pos
                            })
                        elif premio == "-3 Casillas":
                            nueva_pos = max(session.board_state["positions"][user] - 3, 0)
                            session.board_state["positions"][user] = nueva_pos
                            actualizar_casilla(game_id, user, nueva_pos)
                            await session.broadcast({
                                "type": "player_moved",
                                "user": user,
                                "nueva_casilla": nueva_pos
                            })
                        elif premio == "+3 Monedas":
                            session.board_state["balances"][user] += 3
                            await session.broadcast({
                                "type": "balances_changed",
                                "balances": session.board_state["balances"]
                            })
                        elif premio == "-3 Monedas":
                            session.board_state["balances"][user] = max(session.board_state["balances"][user] - 3, 0)
                            await session.broadcast({
                                "type": "balances_changed",
                                "balances": session.board_state["balances"]
                            })

                    else:  # Intercambiamos posición con otro jugador aleatorio
                        jugadores_disponibles = [p_id for p_id in session.players.keys() if p_id != user and session.players[p_id] is not None]
                        if jugadores_disponibles:
                            objetivo = random.choice(jugadores_disponibles)

                            # Intercambiamos posiciones
                            pos_user = session.board_state["positions"][user]
                            pos_objetivo = session.board_state["positions"][objetivo]

                            session.board_state["positions"][user] = pos_objetivo
                            session.board_state["positions"][objetivo] = pos_user

                            actualizar_casilla(game_id, user, pos_objetivo)
                            actualizar_casilla(game_id, objetivo, pos_user)

                            await session.broadcast({
                                "type": "player_moved",
                                "user": user,
                                "nueva_casilla": pos_objetivo,
                                "message": "Posiciones intercambiadas con otro jugador aleatoriamente"
                            })

                            await session.broadcast({
                                "type": "player_moved",
                                "user": objetivo,
                                "nueva_casilla": pos_user,
                                "message": "Posiciones intercambiadas con otro jugador aleatoriamente"
                            })

                if tipo_casilla == 'barrera':
                    if session.board_state["characters"].get(user) == "Escapista":   # Si el jugador es el escapista, solo pierde 1 turno
                        extra -= 1

                    session.penalizacion_pendiente += extra   # El jugador pierde turnos
                    await session.broadcast({
                        "type": "penalizacion_actualizada",
                        "user": user,
                        "penalizacion": session.board_state["penalty_turns"][user]
                    })
                
            case "select_mini":
                if session.board_state["characters"].get(user) == "Videojugador":   # Si el user es el videojugador, iniciamos minijuego
                    minijuego = payload["minijuego"]
                    session.minijuego_actual = minijuego #TEnemos que guardarlo en la sesión también para después saber cómo evaluar las posiciones según el tipo de minijuego
                    descripcion = payload["descripcion"]
                    session.minijuego_participantes = list(session.players.keys()) # Participan todos los jugadores
                    session.minijuego_tipo = "orden"

                    match minijuego:
                        case "Tren":
                            vagones, total_pasajeros = sortear_vagones()
                            # Objetivo es el número de pasajeros en total y vagones los índices de los vagones que hay que mostrar
                            session.minijuego_detalles = {"objetivo": total_pasajeros, "vagones": vagones}
                        case "Reflejos":
                            session.minijuego_detalles = {"objetivo": random.randint(2000, 5000)}    # Valores en ms
                        case "Mayor o Menor":
                            # Generamos 4 cartas aleatorias para cada jugador. El valor de la carta será la puntuación que tengan que enviar los jugadores al acabar el minijuego
                            session.minijuego_detalles = {"cartas": [v + random.randint(0, 3) * 13 for v in random.sample(range(13), 4)]}
                        case "Cronometro ciego":
                            session.minijuego_detalles = {"objetivo": random.randint(7, 10)}    # Segundos que el jugador tiene que contar
                        case "Cortar pan":
                            session.minijuego_detalles = {"objetivo": 50}    # Mitad del pan

                    await session.broadcast({
                        "type": "ini_minijuego",
                        "minijuego": minijuego,
                        "descripcion": descripcion,
                        "estado_partida": session.board_state,
                        # En el caso de tren y cronometro ciego es un objetivo a conseguir, 
                        # en el caso de reflejos es un tiempo a superar y en mayor o menor son las cartas 
                        # que se han repartido a los jugadores
                        "detalles": session.minijuego_detalles
                    })
                        
            case "banquero":
                if session.board_state["characters"].get(user) == "Banquero":
                    # Obtenemos el orden del jugador para esta ronda
                    playerId = session.board_state
                    orden = session.board_state["order"]

                    if orden is None:
                        return

                    # A quién le toca tirar ahora
                    
                    if orden != turno_actual:
                        await session.players[user].send_json({
                            "error": f"No es tu turno. Le toca al jugador {turno_actual}"
                        })
                        return
                    
                    penalizado = payload["robar_a"]     # Usuario al que robamos

                    # Si es el escapiste solo le podemos quitar 1
                    if session.board_state["characters"].get(penalizado) == "Escapista":
                        if session.board_state["balances"][penalizado] > 0: # Si tiene mínimo 1 moneda se la quitamos
                            session.board_state["balances"][user] += 1
                            session.board_state["balances"][penalizado] -= 1

                        # enviamos json aunque no se produzca el robo por falta de monedas
                        await session.broadcast({
                            "type": "balances_changed",
                            "balances": session.board_state["balances"]
                        })

                    else:   # Si no es el escapista le quitamos 2
                        if session.board_state["balances"][penalizado] > 1: # Si tiene mínimo 2 monedas se la quitamos
                            session.board_state["balances"][user] += 2
                            session.board_state["balances"][penalizado] -= 2

                        # enviamos json aunque no se produzca el robo por falta de monedas
                        await session.broadcast({
                            "type": "balances_changed",
                            "balances": session.board_state["balances"]
                        })
                else: 
                    await session.players[user].send_json({
                        "error": f"No eres banquero"
                    })
            
            case "score_minijuego":
                score = payload["score"]

                if session.minijuego_actual in ["Doble o Nada", "Mano de Poker"]:
                    # Comprobamos que la apuesta sea válida
                    if score < 0 or score > session.board_state["balances"].get(user, 0):
                        await session.players[user].send_json({
                            "error": "La apuesta debe ser un número positivo y menor o igual a tu saldo"
                        })
                        return
                    else:
                        session.minijuego_scores[user] = score
                else:
                    session.minijuego_scores[user] = score
                
                # Comprobamos si todos los que debían jugar han terminado
                if all(p in session.minijuego_scores for p in session.minijuego_participantes):
                    await resolver_minijuego(session)

            case "poker_accion":
                # El frontend envía: {"action": "poker_accion", "decision": "apostar" | "retirarse", "cantidad": 50}
                decision = payload.get("decision")
                cantidad = payload.get("cantidad", 0)

                if user not in session.poker_activos:
                    return # Si ya se retiró o no juega, ignoramos

                if decision == "apostar":
                    ya_apostado = session.poker_apuestas_acumuladas.get(user, 0)
                    total_usuario = ya_apostado + cantidad
                    
                    # Verificamos si iguala la apuesta actual
                    if total_usuario < session.poker_apuesta_actual:
                        await session.players[user].send_json({
                            "type": "error",
                            "message": f"Debes igualar la apuesta actual ({session.poker_apuesta_actual}). Te faltan {session.poker_apuesta_actual - ya_apostado} monedas."
                        })
                        return

                    if cantidad < 0 or total_usuario > session.board_state["balances"].get(user, 0):
                        await session.players[user].send_json({"error": "Apuesta inválida o saldo insuficiente."})
                        return

                    session.poker_apuestas_acumuladas[user] = total_usuario
                    
                    # Si sube la apuesta, reseteamos las respuestas de los demás para que tengan que igualar
                    if total_usuario > session.poker_apuesta_actual:
                        session.poker_apuesta_actual = total_usuario
                        # Mantenemos solo la respuesta del que acaba de subir
                        session.poker_respuestas_fase = {user: {"decision": "apostar", "cantidad": total_usuario}}
                        
                        await session.broadcast({
                            "type": "poker_apuesta_actualizada",
                            "user": user,
                            "nueva_apuesta_objetivo": total_usuario,
                            "mensaje": f"{user} ha subido la apuesta a {total_usuario}!"
                        })
                    else:
                        session.poker_respuestas_fase[user] = {"decision": "apostar", "cantidad": total_usuario}
                
                elif decision == "retirarse":
                    session.poker_respuestas_fase[user] = {"decision": "retirarse", "cantidad": 0}

                # Si todos los activos ya han respondido en esta fase, avanzamos la partida
                if len(session.poker_respuestas_fase) == len(session.poker_activos):
                    await avanzar_fase_poker(session)     


                    
            case "comprar_objeto":
                nombre_objeto = payload["objeto"]
                
                # Comprobar que es su turno
                orden = session.board_state["order"].get(user)
                turno_actual = session.players_en_fin_ronda + 1
                
                if orden != turno_actual:
                    await session.players[user].send_json({
                        "error": "No puedes comprar objetos porque no es tu turno."
                    })
                    return
                
                # Comprpobar si se ha movido ya o no
                if session.ha_movido_en_turno:
                    await session.players[user].send_json({
                        "error": "Ya has tirado los dados. Los objetos se compran y usan antes de mover."
                    })
                    return

                # Obtenemos precio de la base de datos con una query en una función porqeu es ineficiente hacerlo con endpoints
                # desde el propio back
                precio = obtener_precio_objeto_db(nombre_objeto)
                
                if precio is None:
                    await session.players[user].send_json({
                        "error": "El objeto seleccionado no existe en la tienda."
                    })
                    return

                #COMPROBAR SALDO Y COMPRA
                saldo_actual = session.board_state["balances"].get(user, 0)

                if saldo_actual < precio:
                    await session.players[user].send_json({
                        "error": f"No tienes suficientes monedas. Cuesta {precio} y tienes {saldo_actual}."
                    })
                    return

                # Tiene saldo compra y usa el objeto
    
                session.board_state["balances"][user] -= precio
                
                await session.broadcast({
                    "type": "balances_changed",
                    "balances": session.board_state["balances"]
                })
                
                if nombre_objeto == "Avanzar Casillas":
                    session.avance_extra += 1
                
                elif nombre_objeto == "Mejorar Dados":
                    orden_tirada = session.board_state["order"].get(user) - 1
                    if orden_tirada != 0: # Solo si no tienes el dado de oro
                        # Tiramos de nuevo los dados con el orden de jugador disminuido en uno para mejorar su segundo dado de nivel
                        session.dados["izq"][orden_tirada], session.dados["der"][orden_tirada], _ = tirarDados(orden_tirada)

                    else: 
                        await session.players[user].send_json({
                        "error": "No puedes usar este objeto porque tienes el dado de oro."
                        })
                        return
                    
                elif nombre_objeto == "Barrera":
                    # El jugador elige a quien penalizar
                    objetivo = payload.get("penalizar_a")
                    
                    if objetivo is None:
                        await session.players[user].send_json({
                            "error": "Debes especificar un objetivo para usar este objeto."
                        })
                        return
                    
                    if objetivo == user:
                        await session.players[user].send_json({
                            "error": "No puedes usar este objeto sobre ti mismo."
                        })
                        return

                    if objetivo not in session.players.keys():
                        await session.players[user].send_json({
                            "error": "El objetivo especificado no es válido."
                        })
                        return

                    # Si es el escapista no le penalizamos
                    if session.board_state["characters"].get(objetivo) == "Escapista":
                        await session.players[user].send_json({
                            "error": "No puedes usar este objeto sobre el Escapista."
                        })
                        return
                    
                    else:   # Tenemos que comprobar si el objetivo ha tirado o no ha tirado, en el segundo caso nos guardamos la penalización
                        session.penalizacion_pendiente[objetivo] += 1
                            
                        await session.broadcast({
                            "type": "penalizacion_anyadida",
                            "user": objetivo,
                            "message": f"Perderás un turno en cuanto termines de tirar los dados"
                        })

                elif nombre_objeto in ["Salvavidas", "Salvavidas bloqueo"]:
                    if session.board_state["penalty_turns"][user] > 0:   # Solo se puede usar si tiene penalización
                        session.board_state["penalty_turns"][user] = 0
                        await session.broadcast({
                            "type": "penalizacion_eliminada",
                            "user": user,
                            "message": "Salvavidas usado para eliminar penalización de barrera"
                        })

                # Avisar de que se ha usado un objeto
                await session.broadcast({
                    "type": "objeto_usado",
                    "user": user,
                    "objeto": nombre_objeto
                })
            
            case "fin_turno":
                if session.board_state["turn"] == session.players:
                    session.board_state["turn"] = 1
                    session.board_state["round"] += 1 

                    session.dados["izq"] = []
                    session.dados["der"] = []
                    sumas = []
                    for i in range(4):

                        dadoizq, dadoder, _ = tirarDados(i + 1)  # hacer 4 tiradas y guardarlas
                        session.dados["izq"].append(dadoizq)
                        session.dados["der"].append(dadoder)
                        sumas.append(dadoizq + dadoder)

                    for p_id in session.players_id:
                        session.board_state["balances"][p_id] += 3

                    # Aviso de las monedas
                    await session.broadcast({
                        "type": "balances_changed",
                        "balances": session.board_state["balances"]
                    })

                    # Avisamos al visionario
                    for p_id, personaje in session.board_state["characters"].items():
                        if personaje == "Vidente":
                            await session.players.get(p_id).send_json({
                                "type": "dice_shown",
                                "punt": sumas
                            })
                        
                        if personaje == "Videojugador":
                            minijuegos = listar_minijuegos_eleccion()
                            dos_minijuegos = random.sample(minijuegos, 2)

                            await session.players.get(p_id).send_json({
                                "type": "choose_minijuego",
                                "minijuegos": dos_minijuegos
                            })
                
                session.board_state["turn"] += 1
                turno_actual = session.board_state["turn"]
                playerId = next((p_id for p_id, pos in session.board_state["order"].items() if pos == turno_actual), None)
                if playerId and session.players.get(playerId) is not None:
                    
                    penalizaciones = session.board_state["penalty_turns"][playerId]
                    if penalizaciones > 0:
                        session.board_state["penalty_turns"][playerId] -= 1
                        await session.broadcast({
                            "type": "penalizacion_actualizada",
                            "user": playerId,
                            "penalizacion": session.board_state["penalty_turns"][playerId]
                        })
                    else:

                        await session.broadcast({
                            "type": "turno_de",
                            "nombre_jugador": playerId,
                            "ronda": session.board_state["round"]
                        }) 
        
                    
                
                

manager = GameManager()