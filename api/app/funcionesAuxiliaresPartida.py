
from random import randint

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
