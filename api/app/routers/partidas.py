from schemas import JoinPartida
from database import get_db_connection

from fastapi import APIRouter, HTTPException, status
from typing import List,Dict
import psycopg2
from modulos.conexionEsperarPartida import ConnectionManager

router = APIRouter()

MAX_JUGADORES = 4  # Definir el número máximo de jugadores por partida
connection_manager = ConnectionManager()

# ---------------------------------------------------------
# OBTENER PARTIDAS ACTIVAS (GET)
# ---------------------------------------------------------
@router.get("/", response_model=List[int])
def obtener_partidas_activas():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT id FROM PARTIDAS.PARTIDA_ACTIVA"
        cursor.execute(query)
        
        resultado = cursor.fetchall() # Trae TODOS
        
        if not resultado:
            raise HTTPException(status_code=404, detail="No hay partidas activas")
            
        return [row['id'] for row in resultado]  # Devolver solo los IDs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# CREAR PARTIDA (POST)
# ---------------------------------------------------------
@router.post("/crear_partida", status_code=status.HTTP_201_CREATED, response_model=int)
def crear_partida(usuario: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que el usuario existe
        if(not verificar_usuario(cursor, usuario)):
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

        cursor.execute(query_crear_jugando, (usuario, nueva_partida_id,))

        conn.commit()
        return nueva_partida_id
        
    except psycopg2.IntegrityError as e:
        conn.rollback() #  deshacer si hay error
        raise HTTPException(status_code=400, detail=str(e))
        
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
async def unirse_partida(usuario: JoinPartida):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # VIGILAR QUE UNA PARTIDA NO SE LLENE

        # Verificar que el usuario existe
        if(not verificar_usuario(cursor, usuario.usuario)):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Verificar que existe la partida
        query_partida = "SELECT id FROM PARTIDAS.PARTIDA_ACTIVA WHERE id = %s"
        cursor.execute(query_partida, (usuario.id_partida,))
        resultado_partida = cursor.fetchone()
        
        if not resultado_partida:
            raise HTTPException(status_code=404, detail="Partida no encontrada")

        # Asignar el jugador a la partida creada
        query_crear_jugando = "INSERT INTO PARTIDAS.JUGANDO (nombre_jugador, id_partida, personaje, dinero, casilla, numero) " \
                                "VALUES (%s, %s, NULL, 0, 1, 1)"

        cursor.execute(query_crear_jugando, (usuario.usuario, usuario.id_partida,))

        query_conteo = "SELECT COUNT(*) as total FROM PARTIDAS.JUGANDO WHERE id_partida = %s"
        cursor.execute(query_conteo, (usuario.id_partida,))
        resultado_conteo = cursor.fetchone()
        cantidad_actual = resultado_conteo['total']

        conn.commit()

        return usuario.id_partida
        
    except psycopg2.IntegrityError as e:
        conn.rollback() #  deshacer si hay error
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cursor.close()
        conn.close()

# AÑADIR BORRADO DE PARTIDA Y ABANDONAR PARTIDA??


# ---------------------------------------------------------
# PARTIDA ACTUAL
# ---------------------------------------------------------

# ---------------------------------------------------------
# Actualizar casilla de jugador
# ---------------------------------------------------------

def actualizar_casilla(game_id: int, player: str, nueva_casilla: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Validación sin HTTPException
        if not verificar_usuario(cursor, player):
            raise ValueError(f"Usuario {player} no encontrado")
        
        # 2. psycopg2 usa SIEMPRE %s (incluso para los int)
        query_partida = """
            UPDATE PARTIDAS.JUGANDO 
            SET casilla = %s 
            WHERE nombre_jugador = %s AND id_partida = %s
        """
        
        cursor.execute(query_partida, (nueva_casilla, player, game_id))
        
        # Guardamos los cambios
        conn.commit()
        return True

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

async def verificar_usuario(cursor, user: str):
    query_usuario = "SELECT nombre FROM USUARIOS.USUARIO WHERE nombre = %s"
    cursor.execute(query_usuario, (user,))
    resultado_usuario = cursor.fetchone()
    
    if not resultado_usuario:
        return False