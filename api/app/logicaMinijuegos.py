import random
from funcionesAuxiliaresPartida import *

async def resolver_minijuego(session):
    if session.minijuego_tipo == "orden":
        await finalizar_minijuego_orden(session)
    elif session.minijuego_tipo == "casilla":
        await finalizar_minijuego_casilla(session)

    # Reiniciamos las variables (cuidado con Poker, porque es por rondas)
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
        "type": "minijuego_resultados",
        "resultados": resultados_front,
        "nuevo_orden": session.board_state["order"]
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

    # Enviamos un solo mensaje con el cambio de monedas
    await session.broadcast({
        "type": "balances_changed",
        "balances": session.board_state["balances"]
    })

async def finalizar_minijuego_dobleNada(session):
    apuesta = session.minijuego_scores[session.minijuego_participantes[0]] # Solo hay un jugador en este minijuego

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