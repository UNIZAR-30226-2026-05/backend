from schemas import JoinPartida
from database import get_db_connection

from fastapi import APIRouter, HTTPException, status, WebSocket
from typing import List,Dict
import psycopg2
from modulos.conexionEsperarPartida import ConnectionManager

router = APIRouter()

MAX_JUGADORES = 4  # Definir el número máximo de jugadores por partida
manager = ConnectionManager()

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
        query_usuario = "SELECT nombre FROM USUARIOS.USUARIO WHERE nombre = %s"
        cursor.execute(query_usuario, (usuario,))
        resultado_usuario = cursor.fetchone()
        
        if not resultado_usuario:
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
        query_usuario = "SELECT nombre FROM USUARIOS.USUARIO WHERE nombre = %s"
        cursor.execute(query_usuario, (usuario.usuario,))
        resultado_usuario = cursor.fetchone()
        
        if not resultado_usuario:
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

        if cantidad_actual >= MAX_JUGADORES:
            await manager.broadcast_to_room(usuario.id_partida, {
                "evento": "PARTIDA_LLENA",
                "mensaje": "La partida está lista para comenzar",
                "id_partida": usuario.id_partida
            })

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


# Router Web-Sockets

@router.websocket("/ws/{partida_id}")
async def websocket_endpoint(websocket: WebSocket, partida_id: int):
    await manager.connect(websocket, partida_id)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket, partida_id)
