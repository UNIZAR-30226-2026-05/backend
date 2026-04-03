
# Controla todos los juegos activos que hay actualmente y se encarga de anunciar
# a los jugadores que estan esperando que ha iniciado la partida

from fastapi import WebSocket
from routers.partidas import *
from routers.juego import *
from funcionesAuxiliaresPartida import *
from typing import Literal
from routers.juego import *
import random

MAX_JUGADORES_DEBUG = 1
META = 50

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
            
            self.minijuego_actual = None
            self.minijuego_detalles = {} # {"objetivo": 10, "cartas": [3, 15, 27, 40], ...}
            self.minijuego_scores = {}   # {"Edu1": 350, "Edu2": 410..., "Edu4": 290}
            self.ha_movido_en_turno = False #Para saber si spuede o no usar objetos
        
        @property
        def is_full(self):
            return len(self.players) == MAX_JUGADORES_DEBUG
        
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
        
        #Cuando se une el primer jugador
        if "positions" not in session.board_state:
            session.board_state["positions"] = {} # Casilla en la que está cada jugador
            session.board_state["balances"] = {} # Dinero que le queda a cada jugador
            session.board_state["characters"] = {} # Personaje para cada jugador
            session.board_state["turns"] = {} # Ronda en la que nos encontramos
            session.board_state["order"] = {} # Orden de tirada para cada ronda
            session.board_state["inventory"] = {} # Objetos que han adquirido los usuarios
            
        if player_id not in session.board_state["positions"]:
                    session.board_state["positions"][player_id] = 0 # Todos los jugadores empiezan en la casilla 0
                    session.board_state["balances"][player_id] = 1
                    session.board_state["turns"][player_id] = 1
                    session.board_state["order"][player_id] = len(session.players)
                    session.board_state["inventory"][player_id] = [] # Cuando se une un usuario no tiene objetos

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

                    await session.broadcast({
                        "type": "player_disconnected",
                        "players_connected": [p for p in session.players.keys()],
                        "message": f"Jugador {player_id} se ha desconectado"
                    })

                elif session.status == "ENDING":
                    del session.players[player_id]  # Eliminamos al jugador desconectado

                    if session.players.len() == 0:
                        del self.active_games[game_id]  # Si no queda nadie eliminamos la partida
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

                    if num_personajes + 1 == MAX_JUGADORES_DEBUG:         # Fin de elecciones -> Inicio de partida real
                        await session.broadcast({
                            "type": "all_players_selected",
                            "message": "Fin de elección de personajes"
                        })

            case "move_player":
                # Obtenemos el orden del jugador para esta ronda
                orden = session.board_state["order"].get(user)

                if orden is None:
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

                nueva_casilla = session.board_state["positions"].get(user) + dado1 + dado2
                
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
                    nueva_casilla = session.board_state["positions"].get(user) + extra
                    session.board_state["positions"][user] = nueva_casilla
                    actualizar_casilla(game_id, user, nueva_casilla)
                    await session.broadcast({
                        "type": "player_moved",
                        "user": user,
                        "nueva_casilla": nueva_casilla
                    })

                # VIGILAR CASO EN EL QUE HAYA DOS JUGADORES EN LA MISMA CASILLA (DILEMA PRISIONERO)

                if tipo_casilla == 'mini':
                    # Tenemos que avisar al frontend del minijuego que ha caído
                    await session.broadcast({
                        "type": "minijuego_casilla",
                        "user": user,
                        "minijuego": extra,
                        "descripcion": obtener_descripcion_minijuego_casilla(extra)
                    })


                if tipo_casilla == 'obj':
                    # Tenemos que avisar al frontend del objeto que ha caído
                    if extra == 1:   # Tenemos que sortear un objeto aleatorio para el jugador
                        objeto = obtener_objeto_aleatorio()
                        await session.broadcast({
                            "type": "obtener_objeto",
                            "user": user,
                            "objeto": objeto["nombre"],
                            "descripcion": objeto["descripcion"]
                        })

                    else:  # Tenemos que intercambiar objetos entre jugadores. Avisamos al usuario para que elija con quién intercambiar
                        await session.players[user].send_json({
                            "type": "intercambiar_objeto",
                            "message": "Elige un jugador para intercambiar objeto",
                        })

                if tipo_casilla == 'barrera':
                    # Ya habremos comunicado la penalización con broadcast, ahora tenemos que apuntarnosla
                    apuntar_penalizacion(game_id, user, extra) # TODO: tenemos que añadir variables y mirar si es el escapista
                                                               # para reducir la penalización. NO REALIZAR FUNCIÓN, HACERLO INLINE
                
            case "end_round":
                session.players_en_fin_ronda += 1

                # Si los 4 han acabado la ronda lanzar dados y avisar al visionario
                if session.players_en_fin_ronda == MAX_JUGADORES_DEBUG:
                    session.players_en_fin_ronda = 0
                    
                    session.dados["izq"] = []
                    session.dados["der"] = []
                    sumas = []
                    for i in range(4):

                        dadoizq, dadoder, _ = tirarDados(i + 1)  # hacer 4 tiradas y guardarlas
                        session.dados["izq"].append(dadoizq)
                        session.dados["der"].append(dadoder)
                        sumas.append(dadoizq + dadoder)

                    for p_id in session.board_state["turns"]:
                        session.board_state["turns"][p_id] += 1
                        session.board_state["balances"][p_id] += 1

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
                
            case "ini_round":
                if session.board_state["characters"].get(user) == "Videojugador":   # Si el user es el videojugador, iniciamos minijuego
                    minijuego = payload["minijuego"]
                    session.minijuego_actual = minijuego #TEnemos que guardarlo en la sesión también para después saber cómo evaluar las posiciones según el tipo de minijuego
                    descripcion = payload["descripcion"]

                    match minijuego:
                        case "Tren":
                            # REVISAR ALEATORIO
                            session.minijuego_detalles = {"objetivo": random.randint(1, 20)}                 
                        case "Reflejos":
                            session.minijuego_detalles = {"objetivo": random.randint(2000, 5000)}    # Valores en ms
                        case "Mayor o Menor":
                            # Generamos 4 cartas aleatorias para cada jugador. El valor de la carta será la puntuación que tengan que enviar los jugadores al acabar el minijuego
                            session.minijuego_detalles = {"cartas": [v + random.randint(0, 3) * 13 for v in random.sample(range(13), 4)]}
                        case "Cronometro ciego":
                            session.minijuego_detalles = {"objetivo": random.randint(5, 15)}    # Segundos que el jugador tiene que contar
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
                    orden = session.board_state["order"].get(user)

                    if orden is None:
                        return

                    # A quién le toca tirar ahora
                    turno_actual = session.players_en_fin_ronda + 1

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
                session.minijuego_scores[user] = score
                
                 # Si ya han terminado el minijeugo los 4 jugadores
                if len(session.minijuego_scores) == MAX_JUGADORES_DEBUG:
                    
                    # Ordenar según el minijuego que sea
                    if session.minijuego_actual == "Reflejos":
                        # En el de reflejos gana el menor tiempo (de menor a mayor)
                        
                            #items() convierte el diccionario {"Edu1": 300, "Edu2": 200...} en una lista de tuplas:
                            #[("Edu1", 300), ("Edu2", 200)...]. Con key indicamos la parte de la tupla en la que se tiene
                            # que basar para ordenar.
                        ranking = sorted(session.minijuego_scores.items(), key=obtener_puntuacion)
                        
                    elif session.minijuego_actual == "Mayor o Menor":
                        # Gana la carta más alta. Ordenamos de mayor a menor con reverse=True
                        ranking = sorted(session.minijuego_scores.items(), key=obtener_puntuacion, reverse=True)
                        
                    else:
                        # Por defecto nos quedamos con el valor absoluto de la diferencia entre la puntuación del jugador y la referencia del minijuego (tiempo objetivo, valor objetivo de la carta, etc). El ganador será el que esté más cerca del
                        objetivo = payload["objetivo"]
                        ranking = ordenar_por_cercania(session.minijuego_scores.items(), objetivo)

                    deshacer_empates(ranking)

                    # Vamos rellenando un diccionario con la posición de cada usuairo y la puntuación que ha conseguido
                    # para después hacer un broadcast con todo al frontend
                    resultados_front = {}
                    
                    for indice, (player_id, puntuacion) in enumerate(ranking):
                        posicion = indice + 1
                        
                        # IMPORTANTE ACTUALIZAR EL ORDEN DEL ESTADO DE LA PARTIDA
                        session.board_state["order"][player_id] = posicion
                        
                        # Rellenamos resulado para este jugador
                        resultados_front[player_id] = {
                            "posicion": posicion,
                            "score": puntuacion
                        }
                    
                    #Limpieza ante ssiguiente ronda
                    session.minijuego_scores = {}
                    session.minijuego_actual = None

                    await session.broadcast({
                        "type": "minijuego_resultados",
                        "resultados": resultados_front,
                        "nuevo_orden": session.board_state["order"]
                    })   
                    
            case "obtener_objeto":
                nombre_objeto = payload["objeto"]
                
                # Metemos el objeto en el inventario del jugador
                session.board_state["inventory"][user].append(nombre_objeto)
                
                # Avisamos a todos 
                await session.broadcast({
                    "type": "inventory_updated",
                    "user": user,
                    "objeto_obtenido": nombre_objeto,
                    "inventario_actual": session.board_state["inventory"][user]
                })
                    
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

                if saldo_actual >= precio:

                    session.board_state["balances"][user] -= precio
                    session.board_state["inventory"][user].append(nombre_objeto)
                    
                    await session.broadcast({
                        "type": "balances_changed",
                        "balances": session.board_state["balances"]
                    })

                    await session.broadcast({
                        "type": "inventory_updated",
                        "user": user,
                        "objeto_obtenido": nombre_objeto,
                        "inventario_actual": session.board_state["inventory"][user]
                    })
                    
                else:
                    await session.players[user].send_json({
                        "error": f"No tienes suficientes monedas. Cuesta {precio} y tienes {saldo_actual}."
                    })
            
            case "usar_objeto":

                #IMPORTANTE!!!!!!!!!!!!!!!!!!!!!!!!!!!!11
                # FALTA POR GESTIONAR QUE SI LO QUE QUIERE USAR ES ALGO QEU TE DA VENTAJA TI LO PUEDES USAR EN EL MISMO
                # TURNO DE LA COMPRA, PERO SI ES ALGO PARA FASTIDIAR A LOS DEMÁS NO HA PODIDO SER OCMPRADO EN ESTA MISMA RONDA

                nombre_objeto = payload.get("objeto")
                
                # Comprobar turno
                orden = session.board_state["order"].get(user)
                turno_actual = session.players_en_fin_ronda + 1
                
                if orden != turno_actual:
                    await session.players[user].send_json({
                        "error": "No puedes usar objetos porque no es tu turno."
                    })
                    return
                
                # Comprobnar si ya se ha movido
                if getattr(session, "ha_movido_en_turno", False):
                    await session.players[user].send_json({
                        "error": "Ya has tirado los dados. Los objetos se usan antes de mover."
                    })
                    return

                # Comprobar si tiene el objeto que quiere usar
                inventario_jugador = session.board_state["inventory"].get(user, [])
                
                if nombre_objeto not in inventario_jugador:
                    await session.players[user].send_json({
                        "error": f"No tienes el objeto '{nombre_objeto}' en tu inventario."
                    })
                    return

                # Gastar objeto (solo borra una unidad si tiene varios iguales)
                session.board_state["inventory"][user].remove(nombre_objeto)

                # -EFECTO DEL OBJETO:
                # Aquí iremos metiendo la lógica según el documento de diseño
                
                #if nombre_objeto == "Avanzar/Retroceder casillas":
                    #...
                    
                # Avisar de que se ha usado un objeto y de la acutalización del inventario
                await session.broadcast({
                    "type": "objeto_usado",
                    "user": user,
                    "objeto": nombre_objeto,
                    "inventario_actual": session.board_state["inventory"][user],
                })
manager = GameManager()