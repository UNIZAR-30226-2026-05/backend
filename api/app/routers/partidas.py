from schemas import JoinPartida
from database import get_db_connection

from fastapi import APIRouter, HTTPException, status, Depends
from .usuarios import obtener_usuario_actual
from typing import List,Dict
import psycopg2

router = APIRouter()

MAX_JUGADORES = 4  # Definir el número máximo de jugadores por partida

# ---------------------------------------------------------
# OBTENER PARTIDAS ACTIVAS (GET)
# ---------------------------------------------------------
@router.get("/", response_model=List[int])
def obtener_partidas_activas():
    """
    Devuelve una lista de IDs de las partidas activas.
    Si no hay partidas activas, devuelve un error 404 {"detail": "No hay partidas activas"}.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT id FROM PARTIDAS.PARTIDA_ACTIVA"
        cursor.execute(query)
        
        resultado = cursor.fetchall() # Trae TODOS
        
        if not resultado:
            raise HTTPException(status_code=404, detail="No hay partidas activas")
            
        return [row['id'] for row in resultado]  # Devolver solo los IDs
    
    except HTTPException:
        # Dejamos que los errores HTTP que nosotros hemos lanzado (como el 404) fluyan normalmente
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# CREAR PARTIDA (POST)
# ---------------------------------------------------------
@router.post("/crear_partida", status_code=status.HTTP_201_CREATED, response_model=int)
def crear_partida(usuario_actual: str = Depends(obtener_usuario_actual)):
    """
    Crea una nueva partida y asigna al usuario actual como jugador de esa partida.
    Devuelve el ID de la partida creada.

    **ESTE ENDPOINT ESTÁ PROTEGIDO MEDIANTE TOKEN**
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que el usuario existe
        if(not verificar_usuario(cursor, usuario_actual)):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Crear partida activa con valores iniciales
        query_crear_partida = "INSERT INTO PARTIDAS.PARTIDA_ACTIVA (hay_barrera, turno, minijuego, ult_resultado) VALUES (%s, 0, NULL, NULL) " \
                              "RETURNING id"
        hay_barrera = [False] * 72  # Inicializar con 72 barreras falsas
        cursor.execute(query_crear_partida, (hay_barrera,))
        nueva_partida_id = cursor.fetchone()['id']  # Obtener el ID de la nueva partida

        # Asignar el jugador a la partida creada
        query_crear_jugando = "INSERT INTO PARTIDAS.JUGANDO (nombre_jugador, id_partida, personaje, dinero, casilla, numero) " \
                                "VALUES (%s, %s, NULL, 0, 1, 1)"

        cursor.execute(query_crear_jugando, (usuario_actual, nueva_partida_id,))

        conn.commit()
        return nueva_partida_id
        
    except psycopg2.IntegrityError as e:
        conn.rollback() #  deshacer si hay error
        raise HTTPException(status_code=400, detail=str(e))
    
    except HTTPException:
        # Dejamos que los errores HTTP que nosotros hemos lanzado (como el 404) fluyan normalmente
        raise
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cursor.close()
        conn.close()

# ---------------------------------------------------------
# UNIRSE A PARTIDA (POST)
# ---------------------------------------------------------
@router.post("/unirse_partida", status_code=status.HTTP_201_CREATED, response_model=int)
async def unirse_partida(datos: JoinPartida, usuario_actual: str = Depends(obtener_usuario_actual) ):
    """
    Permite unirse a una partida existente y asigna al usuario actual como jugador de esa partida.
    Devuelve el ID de la partida a la que se unió. Si la partida no existe, devuelve un error 404 {"detail": "Partida no encontrada"}.
    y si la partida ya tiene 4 jugadores, devuelve un error 400 {"detail": "La partida está llena"}.

    **ESTE ENDPOINT ESTÁ PROTEGIDO MEDIANTE TOKEN**
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:

        # Verificar que el usuario existe
        if(not verificar_usuario(cursor, usuario_actual)):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Verificar que existe la partida
        query_partida = "SELECT id FROM PARTIDAS.PARTIDA_ACTIVA WHERE id = %s"
        cursor.execute(query_partida, (datos.id_partida,))
        resultado_partida = cursor.fetchone()
        
        if not resultado_partida:
            raise HTTPException(status_code=404, detail="Partida no encontrada")
        
        query_conteo = "SELECT COUNT(*) as num_jugadores FROM PARTIDAS.JUGANDO WHERE id_partida = %s"
        cursor.execute(query_conteo, (datos.id_partida,))
        resultado_conteo = cursor.fetchone()
        
        # Si ya hay 4 jugadores o más, cortamos la ejecución
        if resultado_conteo and resultado_conteo["num_jugadores"] >= 4:
            raise HTTPException(status_code=400, detail="La partida está llena")

        # Asignar el jugador a la partida creada
        query_crear_jugando = "INSERT INTO PARTIDAS.JUGANDO (nombre_jugador, id_partida, personaje, dinero, casilla, numero) " \
                                "VALUES (%s, %s, NULL, 0, 1, 1)"

        cursor.execute(query_crear_jugando, (usuario_actual, datos.id_partida,))

        conn.commit()

        return datos.id_partida
        
    except psycopg2.IntegrityError as e:
        conn.rollback() #  deshacer si hay error
        raise HTTPException(status_code=400, detail=str(e))
    
    except HTTPException:
        # Dejamos que los errores HTTP que nosotros hemos lanzado (como el 404) fluyan normalmente
        raise
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# PARTIDA ACTUAL
# ---------------------------------------------------------

# Actualizar casilla de jugador

def actualizar_casilla(game_id: int, player: str, nueva_casilla: int):
    """
    Permite actualizar la casilla de un jugador en una partida. Devuelve True si la actualización se realizó correctamente, 
    o False si hubo un error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        if not verificar_usuario(cursor, player):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        query_partida = """
            UPDATE PARTIDAS.JUGANDO 
            SET casilla = %s 
            WHERE nombre_jugador = %s AND id_partida = %s
        """
        
        cursor.execute(query_partida, (nueva_casilla, player, game_id))
        
        # Guardamos los cambios
        conn.commit()
        return True
    
    except HTTPException:
        # Dejamos que los errores HTTP que nosotros hemos lanzado (como el 404) fluyan normalmente
        raise
    
    except Exception as e:
        conn.rollback() # Deshacer si hay error
        print(f"Error de BBDD al actualizar casilla: {e}") # Para que tú lo veas en la consola
        return False # Le decimos al GameManager que falló
        
    finally:
        cursor.close()
        conn.close()


# Actualizar casilla de jugador

def actualizar_dinero(game_id: int, player: str, diferencia_saldo: int):
    """
    Permite actualizar el dinero de un jugador en una partida. La diferencia de saldo puede ser positiva (ganancia) o 
    negativa (pérdida). Devuelve True si la actualización se realizó correctamente, o False si hubo un error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:

        if not verificar_usuario(cursor, player):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        query_saldo = """
            SELECT dinero
            FROM PARTIDAS.JUGANDO
            WHERE nombre_jugador = %s and id_partida = %s
        """
        cursor.execute(query_saldo, (player,game_id))

        saldo_actual = cursor.fetchone()
        
        query_partida = """
            UPDATE PARTIDAS.JUGANDO 
            SET dinero = %s 
            WHERE nombre_jugador = %s AND id_partida = %s
        """
        nuevo_saldo = saldo_actual + diferencia_saldo
        cursor.execute(query_partida, (nuevo_saldo, player, game_id))
        
        # Guardamos los cambios
        conn.commit()
        return True
    
    except HTTPException:
        # Dejamos que los errores HTTP que nosotros hemos lanzado (como el 404) fluyan normalmente
        raise
    
    except Exception as e:
        conn.rollback() # Deshacer si hay error
        print(f"Error de BBDD al actualizar casilla: {e}") # Para que tú lo veas en la consola
        return False # Le decimos al GameManager que falló
        
    finally:
        cursor.close()
        conn.close()

# GUARDAR PERSONAJE BBDD

def guardar_personaje(game_id: int, player: str, character: str):
    """
    Permite guardar el personaje elegido por un jugador en la base de datos. Devuelve True si la actualización se realizó
    correctamente, o False si hubo un error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if not verificar_usuario(cursor, player):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        query_partida = """
            UPDATE PARTIDAS.JUGANDO 
            SET personaje = %s 
            WHERE nombre_jugador = %s AND id_partida = %s
        """
        cursor.execute(query_partida, (character, player, game_id))
        
        # Guardamos los cambios
        conn.commit()
        return True
    
    except HTTPException:
        # Dejamos que los errores HTTP que nosotros hemos lanzado (como el 404) fluyan normalmente
        raise
    
    except Exception as e:
        conn.rollback() # Deshacer si hay error
        print(f"Error de BBDD al actualizar casilla: {e}") # Para que tú lo veas en la consola
        return False # Le decimos al GameManager que falló
        
    finally:
        cursor.close()
        conn.close()

# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------

def verificar_usuario(cursor, user: str):
    """
    Permite verificar si un usuario existe en la base de datos. Devuelve True si el usuario existe, o False si no existe.
    """
    query_usuario = "SELECT nombre FROM USUARIOS.USUARIO WHERE nombre = %s"

    cursor.execute(query_usuario, (user,))
    resultado = cursor.fetchone()

    return resultado is not None