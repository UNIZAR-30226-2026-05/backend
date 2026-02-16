from schemas import UsuarioPublico, UsuarioRegistro, MinijuegoInfo, PersonajesInfo, ObjetoResponse
from database import get_db_connection

from fastapi import APIRouter, HTTPException, status
from typing import List, Dict
import psycopg2

router = APIRouter()

@router.get("/juego/c_mov")
def obtener_desplazamiento_casilla(casilla):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT movimiento 
            FROM JUEGO.C_MOV
            WHERE numero = casilla
        """
        # Ejecutamos la query pasando los datos como tupla (para no inyección)
        cursor.execute(query,(casilla))
        
        # Confirmamos los cambios en la BD -> ESto es sobre todo cuando vas cogiendo muchos datos para que se te guarden pero no es imprescindible
        conn.commit()
        
        # COgemos el dato 
        desplazamiento = cursor.fetchone() 
        
        return desplazamiento # Pydantic filtrará el password automáticamente
        
    except psycopg2.IntegrityError:
        conn.rollback() #  deshacer si hay error
        raise HTTPException(status_code=400, detail="El usuario ya existe")
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cursor.close()
        conn.close()


# =================================================================================================================================================
# =================================================================================================================================================
#                                                      ENDPOINTS CASILLAS
# =================================================================================================================================================
# =================================================================================================================================================
# ---------------------------------------------------------
# OBTENER LAS CASILLAS (GET)
# ---------------------------------------------------------
@router.get("/casillas/tipos", response_model=Dict[int,str]) 
def obtener_tipos_casillas():
    """
    Al iniciar la partida, se obtiene un DICCIONARIO con el contenido de cada casilla (clave: número, valor: tipo)
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT numero, tipo
            FROM JUEGO.CASILLA 
        """

        cursor.execute(query)
        
        resultados = cursor.fetchall()

        # Convertimos la lista en un diccionario simple {1: 'normal', 2: '...'}
        diccionario_final = { fila['numero']: fila['tipo'] for fila in resultados }

        return diccionario_final
    
        
    except psycopg2.IntegrityError as e:
        conn.rollback() 
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# OBTENER UN OBJETO ALEATORIO (GET)
# ---------------------------------------------------------
@router.get("/casillas/objeto", response_model=ObjetoResponse) 
def obtener_objeto_aleatorio():
    """
    Cuando se gira la ruleta en una casilla, se obtiene un objeto aleatorio
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT objeto, precio, descripcion
            FROM JUEGO.OBJETO
            ORDER BY RANDOM()
            LIMIT 1; 
        """

        cursor.execute(query)
        
        resultado = cursor.fetchone()

        return resultado
    
        
    except psycopg2.IntegrityError as e:
        conn.rollback() 
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cursor.close()
        conn.close()

# =================================================================================================================================================
# =================================================================================================================================================
#                                                      ENDPOINTS PERSONAJE
# =================================================================================================================================================
# =================================================================================================================================================
# ---------------------------------------------------------
# LEER TODOS LOS PERSONAJES EXISTENTES (GET)
# ---------------------------------------------------------
@router.get("/personajes", response_model=List[PersonajesInfo])
def obtener_listado_personajes():
    """
    Devuelve los personajes existentes en el sistema
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM JUEGO.PERSONAJE"
        cursor.execute(query)
        
        resultado = cursor.fetchall()
        
        if not resultado:
            raise HTTPException(status_code=404)
            
        return resultado
        
    finally:
        cursor.close()
        conn.close()