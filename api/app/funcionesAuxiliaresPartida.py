
from random import randint

# Pre: pos es un int entre 1 y 4 que indica la posición del turno 
#      en el que ha quedado el jugador en un turno
# Post: Devuelve el resultado del primer dado, el resultado del segundo y la suma
#       return dado1, dado2, suma

def tirarDado(pos: int):
    if pos == 1:
        extra = 6
    elif pos == 2:
        extra = 4
    elif pos == 3:
        extra = 2
    else:
        extra = 0

    result1 = randint(1,6) 
    result2 = randint(1,max)
    return result1, result2, result1+result2  
