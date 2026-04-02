
from random import randint
from database import get_db_connection

# Pre: pos es un int entre 1 y 4 que indica la posición del turno 
#      en el que ha quedado el jugador en un turno
# Post: Devuelve el resultado del primer dado, el resultado del segundo y la suma
#       return dado1, dado2, suma

def tirarDados(pos: int):
    if pos == 1:
        extra = 6
    elif pos == 2:
        extra = 4
    elif pos == 3:
        extra = 2
    else:
        extra = 0

    result1 = randint(1,6) 

    if extra != 0:
        result2 = randint(1,extra)
    else: 
        result2 = 0
    
    return result1, result2, result1+result2  

# Cuando tenemos un ranking de un minijiuego en tuplas, queremos obtener el valor numérico
# de la puntuación para poder ordenarlo
def obtener_puntuacion(tupla):
    # 'tupla' es ("Edu1", 300)
    # Devuelve el elemento en la posición 1 (los puntos)
    return tupla[1]

# Obtener ranking según la cercanía a un objetivo. 
# El ranking se ordena de menor a mayor diferencia absoluta entre la puntuación del jugador y el objetivo
def ordenar_por_cercania(minijuego_scores, objetivo: int):
    # Función auxiliar para calcular la diferencia absoluta
    def diferencia(tupla):
        puntuacion = obtener_puntuacion(tupla)
        return abs(puntuacion - objetivo)

    # Ordenar usando la función auxiliar
    return sorted(minijuego_scores, key=diferencia)

import random

def deshacer_empates(ranking: list):
    # Agrupar por puntuación
    grupos = {}
    for nombre, puntuacion in ranking:
        if puntuacion not in grupos:
            grupos[puntuacion] = []
        grupos[puntuacion].append((nombre, puntuacion))
    
    # Ordenar puntuaciones de mayor a menor por grupos
    puntuaciones_ordenadas = sorted(grupos.keys(), reverse=True)
    
    resultado = []
    
    for puntuacion in puntuaciones_ordenadas:
        grupo = grupos[puntuacion]
        
        # Si hay empate mezclamos el grupo de jugadores con la misma puntuación
        if len(grupo) > 1:
            random.shuffle(grupo)
        
        # Añadir al resultado
        resultado.extend(grupo)
    
    return resultado

#Búsqeuda del precio en la bbdd para no llamar a un endpoint desde el backend
def obtener_precio_objeto_db(nombre: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT precio FROM JUEGO.OBJETO WHERE nombre = %s"
        cursor.execute(query, (nombre,))
        resultado = cursor.fetchone()
        
        return resultado["precio"] if resultado else None
    finally:
        cursor.close()
        conn.close()