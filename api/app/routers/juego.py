from schemas import UsuarioPublico, UsuarioRegistro, MinijuegoInfo 
from database import get_db_connection

from fastapi import APIRouter, HTTPException, status
from typing import List
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

@router.get("/juego/c_obj")
def obtener_objeto_casilla(casilla):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT movimiento 
            FROM JUEGO.C_OBJ
            WHERE numero = casilla
        """
        # Ejecutamos la query pasando los datos como tupla (para no inyección)
        cursor.execute(query,(casilla))
        
        # Confirmamos los cambios en la BD -> ESto es sobre todo cuando vas cogiendo muchos datos para que se te guarden pero no es imprescindible
        conn.commit()
        
        # COgemos el dato 
        objeto = cursor.fetchone() 
        
        return objeto # Pydantic filtrará el password automáticamente
        
    except psycopg2.IntegrityError:
        conn.rollback() #  deshacer si hay error
        raise HTTPException(status_code=400, detail="El usuario ya existe")
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cursor.close()
        conn.close()
