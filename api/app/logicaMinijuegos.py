import random
import asyncio
from funcionesAuxiliaresPartida import *

# Definición vagones del tren
vagones_normales = [13, 10, 12, 9]
vagones_especiales = [6, 16, 8, 14]

# Definición de la baraja estándar de póker
numeros = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jota', 'reina', 'rey', 'as']
palos = ['picas', 'corazones', 'treboles', 'diamantes']

# Generamos la baraja indexable
baraja = [(n, p) for n in numeros for p in palos]

# Diccionario para dar valor numérico 
valores_carta = {n: i+2 for i, n in enumerate(numeros)}

async def resolver_minijuego(session):
    if session.minijuego_tipo == "orden":
        await finalizar_minijuego_orden(session)
    elif session.minijuego_tipo == "casilla":
        await finalizar_minijuego_casilla(session)

    # Reiniciamos las variables 
    if session.minijuego_actual != "Mano de Poker": # La mano de poker se reinicia en la propia función
        session.minijuego_actual = None
        session.minijuego_scores = {}
        session.minijuego_participantes = []
        session.minijuego_tipo = None
        session.minijuego_detalles = {}

async def finalizar_minijuego_orden(session):
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
        objetivo = session.minijuego_detalles.get("objetivo")
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

    await session.broadcast({
        "type": "turno_de",
        "nombre_jugador": next((p_id for p_id, pos in session.board_state["order"].items() if pos == 1), ""),
        "ronda": session.board_state["round"]
    })  

async def finalizar_minijuego_casilla(session):
   if session.minijuego_actual == 'Dilema del Prisionero':
       await finalizar_minijuego_dilemaPrisionero(session)
   elif session.minijuego_actual == "Doble o Nada":
        await finalizar_minijuego_dobleNada(session) 
   elif session.minijuego_actual == "Mano de Poker":
        await finalizar_minijuego_poker(session)

async def finalizar_minijuego_dilemaPrisionero(session):
    p1, p2 = session.minijuego_participantes
    d1 = session.minijuego_scores[p1] # "cooperar" o "traicionar"
    d2 = session.minijuego_scores[p2]

    if d1 == "cooperar" and d2 == "cooperar":
        recompensa = {p1: 2, p2: 2}
    elif d1 == "traicionar" and d2 == "traicionar":
        recompensa = {p1: 0, p2: 0}
    elif d1 == "traicionar" and d2 == "cooperar":
        recompensa = {p1: 3, p2: 0}
    else: # Cooperar vs Traicionar
        recompensa = {p1: 0, p2: 3}

    # Aplicar cambios en monedas
    for p_id, monto in recompensa.items():
        session.board_state["balances"][p_id] += monto

    # Enviamos los resultados detallados antes de cerrar para que el frontend los muestre
    await session.broadcast({
        "type": "dilema_resultados",
        "decisiones": {p1: d1, p2: d2},
        "recompensas": recompensa
    })

    # Enviamos un solo mensaje con el cambio de monedas
    await session.broadcast({
        "type": "balances_changed",
        "balances": session.board_state["balances"]
    })

async def finalizar_minijuego_dobleNada(session):
    apuesta = session.minijuego_scores[session.minijuego_participantes[0]] # Solo hay un jugador en este minijuego

    if apuesta > 0:
        victoria = random.random() # Número aleatorio entre 0 y 1. Si es menor a 0.5 pierde, si es mayor a 0.5 gana

        if victoria < 0.5:
            session.board_state["balances"][session.minijuego_participantes[0]] -= apuesta
        else:
            session.board_state["balances"][session.minijuego_participantes[0]] += apuesta

    # Enviamos un solo mensaje con el cambio de monedas
    await session.broadcast({
        "type": "balances_changed",
        "balances": session.board_state["balances"]
    })

async def iniciar_poker_real(session):
    jugadores_ids = session.minijuego_participantes
    num_jugadores = len(jugadores_ids)
    
    # Sorteamos la mesa completa
    manos, mesa = sortearManoPoker(num_jugadores)
    
    session.minijuego_detalles = {
        "manos": manos,
        "mesa_oculta": mesa,
        "mesa_visible": []
    }
    
    session.poker_fase = "pre-flop"
    session.poker_bote = 0
    session.poker_activos = list(jugadores_ids)
    session.poker_respuestas_fase = {}
    session.poker_apuesta_actual = 0
    session.poker_apuestas_acumuladas = {}

    # Enviamos a cada jugador sus cartas y les pedimos su primera acción (Pre-flop)
    for i, p_id in enumerate(jugadores_ids):
        ws = session.players.get(p_id)
        if ws:
            await ws.send_json({
                "type": "poker_inicio_ronda",
                "fase": "pre-flop",
                "mis_cartas": [carta_a_dict(c) for c in manos[i]],
                "mensaje": "¿Te retiras o haces tu primera apuesta?"
            })

async def avanzar_fase_poker(session):
    # 1. Procesar quién se ha retirado
    for p_id, datos in session.poker_respuestas_fase.items():
        if datos["decision"] == "retirarse":
            session.poker_activos.remove(p_id)
            
    # 2. Cobrar las apuestas acumuladas en la fase (incluso a los que acaban de retirarse)
    for p_id, apuesta in session.poker_apuestas_acumuladas.items():
        session.board_state["balances"][p_id] -= apuesta
        session.poker_bote += apuesta

    session.poker_respuestas_fase = {} # Limpiamos para la siguiente ronda
    session.poker_apuesta_actual = 0
    session.poker_apuestas_acumuladas = {}

    # Avisamos de los nuevos saldos y el bote actualizado
    await session.broadcast({
        "type": "balances_changed",
        "balances": session.board_state["balances"]
    })

    # Comprobar si todos se han retirado menos uno
    if len(session.poker_activos) == 1:
        ganador_id = session.poker_activos[0]
        await resolver_showdown_poker(session, ganadores_por_abandono=[ganador_id])
        return
    elif len(session.poker_activos) == 0:
        # Raro, pero si todos se tiran a la vez, el bote se pierde o se devuelve. Lo anulamos.
        await session.broadcast({"type": "info", "message": "Todos se retiraron. Fin de la mano."})
        session.minijuego_actual = None
        return

    # Avanzar a la siguiente fase
    fase_actual = session.poker_fase
    detalles = session.minijuego_detalles
    
    if fase_actual == "pre-flop":
        session.poker_fase = "flop"
        nuevas_cartas = detalles["mesa_oculta"][0:3]
        detalles["mesa_visible"].extend(nuevas_cartas)
        
    elif fase_actual == "flop":
        session.poker_fase = "turn"
        nuevas_cartas = [detalles["mesa_oculta"][3]]
        detalles["mesa_visible"].extend(nuevas_cartas)
        
    elif fase_actual == "turn":
        session.poker_fase = "river"
        nuevas_cartas = [detalles["mesa_oculta"][4]]
        detalles["mesa_visible"].extend(nuevas_cartas)
        
    elif fase_actual == "river":
        # Si llegamos aquí, toca enseñar cartas y ver quién gana de los que quedan
        await resolver_showdown_poker(session, ganadores_por_abandono=[])
        return

    # Enviar el estado actualizado al frontend para que decidan de nuevo
    await session.broadcast({
        "type": "poker_nueva_fase",
        "fase": session.poker_fase,
        "bote_actual": session.poker_bote,
        "mesa_visible": [carta_a_dict(c) for c in detalles["mesa_visible"]],
        "jugadores_activos": session.poker_activos,
        "mensaje": f"Fase {session.poker_fase.upper()}. ¡Hagan sus apuestas!"
    })

# Función para resolver el ganador final
async def resolver_showdown_poker(session, ganadores_por_abandono):
    bote = session.poker_bote
    
    # Si alguien ganó porque los demás se retiraron
    if ganadores_por_abandono:
        ganador_id = ganadores_por_abandono[0]
        session.board_state["balances"][ganador_id] += bote
        await session.broadcast({
            "type": "poker_resultados",
            "id_ganadores": [ganador_id],
            "bote_ganado": bote,
            "resultados_ordenados": [{"user": ganador_id, "mano": "victoria por abandono", "cartas": []}],
            "mesa_completa": [carta_a_dict(c) for c in session.minijuego_detalles.get("mesa_visible", [])],
        })
    
    # Si llegamos al River, evaluamos las cartas
    else:
        jugadores_ids = session.minijuego_participantes
        resultados = []
        
        for i, p_id in enumerate(jugadores_ids):
            if p_id in session.poker_activos:
                mano = session.minijuego_detalles["manos"][i]
                mesa_completa = session.minijuego_detalles["mesa_oculta"]
                
                puntos, kickers = evaluar_jugada(mano + mesa_completa)
                resultados.append({
                    "user": p_id,
                    "cartas": [carta_a_dict(c) for c in mano],
                    "puntuacion_tupla": (puntos, kickers),
                    "mano": nombre_jugada(puntos)
                })
        
        # Ordenar y buscar empates 
        resultados.sort(key=lambda x: x["puntuacion_tupla"], reverse=True)
        mejor_tupla = resultados[0]["puntuacion_tupla"]
        ganadores = [r for r in resultados if r["puntuacion_tupla"] == mejor_tupla]
        
        bote_por_ganador = bote // len(ganadores)
        ids_ganadores = [g["user"] for g in ganadores]
        
        for g_id in ids_ganadores:
            session.board_state["balances"][g_id] += bote_por_ganador
            
        for r in resultados:
            del r["puntuacion_tupla"]
            
        await session.broadcast({
            "type": "poker_resultados",
            "id_ganadores": ids_ganadores,
            "bote_ganado": bote_por_ganador,
            "resultados_ordenados": resultados,
            "mesa_completa": [carta_a_dict(c) for c in session.minijuego_detalles["mesa_oculta"]]
        })
        
    await session.broadcast({
        "type": "balances_changed",
        "balances": session.board_state["balances"]
    })

    # Limpieza total del minijuego
    session.minijuego_actual = None
    session.poker_fase = None
    session.poker_bote = 0
    session.poker_activos = []
    session.poker_respuestas_fase = {}
    session.poker_apuesta_actual = 0
    session.poker_apuestas_acumuladas = {}
    session.minijuego_detalles = {}

async def finalizar_minijuego_poker(session):
    jugadores_ids = session.minijuego_participantes
    num_jugadores = len(jugadores_ids)
    
    # Recoger las apuestas, restarlas de los saldos y crear el bote
    bote_total = 0
    for p_id in jugadores_ids:
        apuesta = session.minijuego_scores.get(p_id, 0)
        session.board_state["balances"][p_id] -= apuesta
        bote_total += apuesta
        
    await session.broadcast({
        "type": "balances_changed",
        "balances": session.board_state["balances"]
    })

    manos, mesa = sortearManoPoker(num_jugadores)
    resultados_jugadores = []
    
    for i, p_id in enumerate(jugadores_ids):
        puntos, kickers = evaluar_jugada(manos[i] + mesa)
        resultados_jugadores.append({
            "user": p_id,
            "cartas": [carta_a_dict(c) for c in manos[i]],
            "puntuacion_tupla": (puntos, kickers),
            "mano": nombre_jugada(puntos)
        })
        
    # Ordenamos usando la tupla (Puntos de jugada + Kickers de desempate)
    resultados_jugadores.sort(key=lambda x: x["puntuacion_tupla"], reverse=True)
    
    # Buscamos empates:
    mejor_tupla = resultados_jugadores[0]["puntuacion_tupla"]
    ganadores = [r for r in resultados_jugadores if r["puntuacion_tupla"] == mejor_tupla]
    
    # Dividimos el bote entre los empatados
    bote_por_ganador = bote_total // len(ganadores)
    ids_ganadores = [g["user"] for g in ganadores]
    
    for r in resultados_jugadores:
        del r["puntuacion_tupla"]
        
    
    # Repartir cartas privadas
    for i, p_id in enumerate(jugadores_ids):
        ws = session.players.get(p_id)
        if ws:
            await ws.send_json({
                "type": "poker_preflop",
                "mis_cartas": [carta_a_dict(c) for c in manos[i]],
                "bote": bote_total
            })
            
    await session.broadcast({"type": "poker_mensaje", "texto": f"Bote de {bote_total} monedas. Repartiendo..."})
    await asyncio.sleep(2)
    
    # Flop
    await session.broadcast({
        "type": "poker_flop",
        "cartas_reveladas": [carta_a_dict(c) for c in mesa[0:3]]
    })
    await asyncio.sleep(2)
    
    # Turn
    await session.broadcast({
        "type": "poker_turn",
        "carta_revelada": carta_a_dict(mesa[3])
    })
    await asyncio.sleep(2)
    
    # River 
    await session.broadcast({
        "type": "poker_river",
        "carta_revelada": carta_a_dict(mesa[4])
    })
    await asyncio.sleep(3) # Tensión final
    
    # Se entrega el bote a los ganadores
    for ganador_id in ids_ganadores:
        session.board_state["balances"][ganador_id] += bote_por_ganador
    
    await session.broadcast({
        "type": "poker_resultados",
        "id_ganadores": ids_ganadores, # Enviamos lista de ganadores
        "bote_ganado": bote_por_ganador,
        "resultados_ordenados": resultados_jugadores,
        "mesa_completa": [carta_a_dict(c) for c in mesa]
    })
    
    await session.broadcast({
        "type": "balances_changed",
        "balances": session.board_state["balances"]
    })

    # Limpiamos las variables de sesión
    session.minijuego_actual = None
    session.minijuego_scores = {}
    session.minijuego_participantes = []
    session.minijuego_tipo = None
    session.minijuego_detalles = {}
    session.poker_apuesta_actual = 0
    session.poker_apuestas_acumuladas = {}

# Dado un indice devuelve la tupla de la carta correspondiente en la baraja. Ej: 0 -> ('as', 'picas'), 51 -> ('rey', 'diamantes')
def indexar_carta(carta):
    if carta < 0 or carta >= len(baraja):
        return None
    
    return baraja[carta]

def puntuar_poker(mano_str):
    puntuaciones = {
        "carta alta": 1, "pareja": 2, "doble pareja": 3, "trio": 4,
        "escalera": 5, "color": 6, "full house": 7, "poker": 8,
        "escalera de color": 9, "escalera real": 10
    }
    return puntuaciones.get(mano_str, 0)

def nombre_jugada(puntos):
    nombres = {
        1: "carta alta", 2: "pareja", 3: "doble pareja", 4: "trio",
        5: "escalera", 6: "color", 7: "full house", 8: "poker",
        9: "escalera de color", 10: "escalera real"
    }
    return nombres.get(puntos, "desconocida")

# La idea es llamar a este vector con las dos cartas de cada jugador más las cartas de la mesa, todas ya indexadas en el vector
def evaluar_jugada(mano):
    """
    Recibe una lista de 7 cartas (2 del jugador + 5 de la mesa).
    Devuelve una tupla: (puntuacion_base, [valores_para_desempate])
    Ejemplo: (2, [14, 13, 8, 5]) -> Pareja de Ases, kickers K, 8, 5
    """
    if not mano or len(mano) < 5:
        return 0, []

    # Convertimos las cartas a su valor numérico y ordenamos de mayor a menor
    cartas = sorted([(valores_carta[c[0]], c[1]) for c in mano], key=lambda x: x[0], reverse=True)
    
    # Contamos apariciones de cada valor y agrupamos por palos
    conteo_val = {}
    conteo_palos = {'picas': [], 'corazones': [], 'treboles': [], 'diamantes': []}
    
    for val, palo in cartas:
        conteo_val[val] = conteo_val.get(val, 0) + 1
        conteo_palos[palo].append(val)

    # --- FUNCIÓN AUXILIAR PARA BUSCAR ESCALERAS ---
    def buscar_escalera(lista_valores):
        # Quitamos duplicados manteniendo el orden
        unicos = []
        for v in lista_valores:
            if v not in unicos: unicos.append(v)
        
        # El As (14) también puede valer 1 para la escalera baja (A, 2, 3, 4, 5)
        if 14 in unicos: 
            unicos.append(1)
        
        consecutivos = []
        for v in unicos:
            if not consecutivos or consecutivos[-1] - 1 == v:
                consecutivos.append(v)
            else:
                if len(consecutivos) >= 5: break
                consecutivos = [v]
            
            if len(consecutivos) == 5:
                return consecutivos[0] # Devolvemos la carta más alta de la escalera
        return None


    # Buscamos si hay Color (5+ del mismo palo)
    color_cartas = None
    for palo, vals in conteo_palos.items():
        if len(vals) >= 5:
            color_cartas = vals # Ya están ordenadas de mayor a menor
            break

    # 1. Escalera Real y Escalera de Color
    if color_cartas:
        alta_esc_color = buscar_escalera(color_cartas)
        if alta_esc_color:
            if alta_esc_color == 14:
                return puntuar_poker("escalera real"), []
            return puntuar_poker("escalera de color"), [alta_esc_color]

    # freq = {cantidad_repeticiones: [valores_carta]}
    freq = {4: [], 3: [], 2: [], 1: []}
    for val, count in conteo_val.items():
        freq[count].append(val)
    for k in freq: 
        freq[k].sort(reverse=True) # Ordenamos los tríos/parejas de mayor a menor

    # 2. Poker
    if freq[4]:
        val_poker = freq[4][0]
        kicker = max([v for v in conteo_val.keys() if v != val_poker])
        return puntuar_poker("poker"), [val_poker, kicker]

    # 3. Full House
    # Puede ser formado por un trío y una pareja, o por dos tríos.
    if freq[3] and (len(freq[3]) > 1 or freq[2]):
        val_trio = freq[3][0]
        candidatos_pareja = freq[2] + (freq[3][1:] if len(freq[3]) > 1 else [])
        val_pareja = max(candidatos_pareja)
        return puntuar_poker("full house"), [val_trio, val_pareja]

    # 4. Color
    if color_cartas:
        return puntuar_poker("color"), color_cartas[:5]

    # 5. Escalera Normal
    alta_esc = buscar_escalera([c[0] for c in cartas])
    if alta_esc:
        return puntuar_poker("escalera"), [alta_esc]

    # 6. Trío
    if freq[3]:
        val_trio = freq[3][0]
        kickers = sorted([v for v in conteo_val.keys() if v != val_trio], reverse=True)[:2]
        return puntuar_poker("trio"), [val_trio] + kickers

    # 7. Doble Pareja
    if len(freq[2]) >= 2:
        pareja1 = freq[2][0]
        pareja2 = freq[2][1]
        kicker = max([v for v in conteo_val.keys() if v not in (pareja1, pareja2)])
        return puntuar_poker("doble pareja"), [pareja1, pareja2, kicker]

    # 8. Pareja
    if freq[2]:
        pareja = freq[2][0]
        kickers = sorted([v for v in conteo_val.keys() if v != pareja], reverse=True)[:3]
        return puntuar_poker("pareja"), [pareja] + kickers

    # 9. Carta Alta
    kickers = sorted(conteo_val.keys(), reverse=True)[:5]
    return puntuar_poker("carta alta"), kickers

def sortearManoPoker(numPlayers: int):

    total_cartas_necesarias = (numPlayers * 2) + 5
    if total_cartas_necesarias > 52:
        raise ValueError("Demasiados jugadores para una sola baraja.")

    indices = random.sample(range(52), total_cartas_necesarias)
    cartas_repartidas = [baraja[i] for i in indices]
    
    manos_jugadores = []

    for i in range(numPlayers):
        mano = [cartas_repartidas[i*2], cartas_repartidas[i*2 + 1]]
        manos_jugadores.append(mano)
        
    mesa = cartas_repartidas[-5:]
    
    return manos_jugadores, mesa

def carta_a_dict(carta):
    return {"valor": carta[0], "palo": carta[1]}

# Función para sortear los vagones en el minijuego del tren
def sortear_vagones():
    total_pasajeros = 0
    vagones = []
    # Primero sorteamos los vagones normales
    for _ in range(3):  
        # Generamos un índice aleatorio válido
        indice = random.randrange(len(vagones_normales))

        # Obtenemos el valor en esa posición
        total_pasajeros += vagones_normales[indice]

        vagones.append(indice) # Añadimos al vector de índices el número del vagón sorteado

    # Para el último vagón, sorteamos entre los especiales
    indice = random.randrange(len(vagones_especiales))
    total_pasajeros += vagones_especiales[indice]
    vagones.append(indice)

    return vagones, total_pasajeros