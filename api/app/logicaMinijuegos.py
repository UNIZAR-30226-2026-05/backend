import random
from funcionesAuxiliaresPartida import *

numeros = ['as', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'jota', 'reina', 'rey']
palos = ['picas', 'corazones', 'treboles', 'diamantes']
baraja = [(numero, palo) for palo in palos for numero in numeros]

async def resolver_minijuego(session):
    if session.minijuego_tipo == "orden":
        await finalizar_minijuego_orden(session)
    elif session.minijuego_tipo == "casilla":
        await finalizar_minijuego_casilla(session)

    # Reiniciamos las variables (cuidado con Poker, porque es por rondas)
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

async def finalizar_minijuego_poker(session):

    # Limpiamos variables una vez ya hemos finalizado varias rondas
    session.minijuego_actual = None
    session.minijuego_scores = {}
    session.minijuego_participantes = []
    session.minijuego_tipo = None
    session.minijuego_detalles = {}

# Dado un indice devuelve la tupla de la carta correspondiente en la baraja. Ej: 0 -> ('as', 'picas'), 51 -> ('rey', 'diamantes')
def indexar_carta(carta):
    if carta < 0 or carta >= len(baraja):
        return None
    
    return baraja[carta]

def puntuar_poker(mano):
    # Asignamos un valor a cada tipo de mano
    if mano is None:
        return 0
    elif mano == "carta alta":
        return 1
    elif mano == "pareja":
        return 2
    elif mano == "doble pareja":
        return 3
    elif mano == "trio":
        return 4
    elif mano == "escalera":
        return 5
    elif mano == "color":
        return 6
    elif mano == "full house":
        return 7
    elif mano == "poker":
        return 8
    elif mano == "escalera de color":
        return 9
    elif mano == "escalera real":
        return 10
    else:
        return 0

# La idea es llamar a este vector con las dos cartas de cada jugador más las cartas de la mesa, todas ya indexadas en el vector
def dar_valor_mano(mano):
    jugada = "escalera real" # Valor más alto posible, para luego ir bajando
    if mano is None:
        return 0
    
    # Buscamos si es escalera real (10, J, Q, K, A del mismo palo)
    if all(carta in mano for carta in [('10', 'picas'), ('jota', 'picas'), ('reina', 'picas'), ('rey', 'picas'), ('as', 'picas')]) or \
       all(carta in mano for carta in [('10', 'corazones'), ('jota', 'corazones'), ('reina', 'corazones'), ('rey', 'corazones'), ('as', 'corazones')]) or \
       all(carta in mano for carta in [('10', 'treboles'), ('jota', 'treboles'), ('reina', 'treboles'), ('rey', 'treboles'), ('as', 'treboles')]) or \
       all(carta in mano for carta in [('10', 'diamantes'), ('jota', 'diamantes'), ('reina', 'diamantes'), ('rey', 'diamantes'), ('as', 'diamantes')]):
        return puntuar_poker(jugada)
    
    # Ya no puede ser escalera real, buscamos si es escalera de color (5 cartas seguidas del mismo palo)
    jugada = "escalera de color"
    for palo in palos:
        for numero in numeros:
            if all(carta in mano for carta in [('6', palo), ('7', palo), ('8', palo), ('9', palo), ('10', palo)]): # COMPLETAR
                return puntuar_poker(jugada)

    # Ya no puede ser escalera de color, buscamos si es poker (4 cartas iguales)
    jugada = "poker"
    for numero in numeros:
        if sum(1 for carta in mano if carta[0] == numero) >= 4:
            return puntuar_poker(jugada)
        
    jugada = "full house"
    tiene_trio = False
    tiene_pareja = False
    for numero in numeros:
        cantidad = sum(1 for carta in mano if carta[0] == numero)
        if cantidad >= 3:
            tiene_trio = True
        elif cantidad >= 2:
            tiene_pareja = True
    if tiene_trio and tiene_pareja:
        return puntuar_poker(jugada)
    
    jugada = "color"
    for palo in palos:
        if sum(1 for carta in mano if carta[1] == palo) >= 5: 
            return puntuar_poker(jugada)
            
            
    
    jugada = "escalera"
    # Para la escalera, es más fácil transformar las cartas a sus índices numéricos.
    # Asumimos que 'numeros' está ordenado, ej: ['2', '3', '4', ..., 'rey', 'as']
    valores_en_mano = set([numeros.index(carta[0]) for carta in mano])
    
    # El As (último índice, por ejemplo 12) también puede actuar como un "1" (índice -1)
    # para formar la escalera menor: As, 2, 3, 4, 5.
    if (len(numeros) - 1) in valores_en_mano: 
        valores_en_mano.add(-1)
        
    consecutivas = 0
    # Revisamos desde -1 hasta la longitud total de 'numeros'
    for i in range(-1, len(numeros)):
        if i in valores_en_mano:
            consecutivas += 1
            if consecutivas >= 5:
                return puntuar_poker(jugada)
        else:
            consecutivas = 0 # Rompemos la racha si falta un número

    jugada = "trio"
    for numero in numeros:
        if sum(1 for carta in mano if carta[0] == numero) >= 3:
            return puntuar_poker(jugada)
            
    # Para Doble Pareja y Pareja, contamos cuántas parejas distintas hay
    cantidad_parejas = 0
    for numero in numeros:
        if sum(1 for carta in mano if carta[0] == numero) >= 2:
            cantidad_parejas += 1
            
    if cantidad_parejas >= 2:
        return puntuar_poker("doble pareja")
    
    if cantidad_parejas == 1:
        return puntuar_poker("pareja")

    # Si no ha entrado en ninguno de los if anteriores, es Carta Alta por descarte
    return puntuar_poker("carta alta")
    