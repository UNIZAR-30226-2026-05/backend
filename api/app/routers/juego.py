from schemas import UsuarioPublico, UsuarioRegistro, MinijuegoInfo, PersonajesInfo, ObjetoResponse
from database import get_db_connection
from funcionesAuxiliaresPartida import obtener_precio_objeto_db
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
    Cuando se gira la ruleta en una casilla, se obtiene un objeto aleatorio de los posibles candidatos que hay en la tabla OBJETO_RULETA
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT o.nombre, o.precio, o.descripcion
            FROM JUEGO.OBJETO_RULETA r
            JOIN JUEGO.OBJETO o 
                ON r.nombre = o.nombre
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

# ---------------------------------------------------------
# LEER MINIJUEGOS (GET) 
# ---------------------------------------------------------
@router.get("/minijuegos/", response_model=List[MinijuegoInfo])
def listar_minijuegos():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM JUEGO.MINIJUEGO")
        
        resultados = cursor.fetchall() # Trae TODOS como una lista
        
        return resultados
        
    finally:
        cursor.close()
        conn.close()

# ---------------------------------------------------------
# LEER MINIJUEGOS ELECCIÓN (GET) 
# ---------------------------------------------------------
@router.get("/minijuegos_eleccion/", response_model=List[MinijuegoInfo])
def listar_minijuegos_eleccion():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM JUEGO.MINIJUEGO_ELECCION")
        
        resultados = cursor.fetchall() # Trae TODOS como una lista
        
        return resultados
        
    finally:
        cursor.close()
        conn.close()

def obtenerTipoCasilla(numCasilla: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT * FROM JUEGO.CASILLA WHERE numero = %s"
        cursor.execute(query,(numCasilla,))
        resultado = cursor.fetchone()

        if resultado:
            return "normal", resultado['tipo']

        query = "SELECT * FROM JUEGO.C_MOV WHERE numero = %s"
        cursor.execute(query,(numCasilla,))
        resultado = cursor.fetchone()
        if resultado:
            return "mov", resultado['movimiento']

        query = "SELECT * FROM JUEGO.C_OBJ WHERE numero = %s"
        cursor.execute(query,(numCasilla,))
        resultado = cursor.fetchone()

        if resultado:
            return "obj", resultado['ruleta']
        
        query = "SELECT * FROM JUEGO.C_MINI WHERE numero = %s"
        cursor.execute(query,(numCasilla,))
        resultado = cursor.fetchone()

        if resultado:
            return "mini", resultado['minijuego']
        
        query = "SELECT * FROM JUEGO.C_BARRERA WHERE numero = %s"
        cursor.execute(query,(numCasilla,))
        resultado = cursor.fetchone()

        if resultado:
            return "barrera", resultado['penalizacion']

        print(f"AVISO: La casilla {numCasilla} no existe en la BD. Asumimos tipo 'normal' y ningun extra.")
        return "normal", None

    finally:
        cursor.close()
        conn.close()

# Función para obtener la descripción de un minijuego de una casilla dado su nombre
def obtener_descripcion_minijuego_casilla(minijuego: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT descripcion FROM JUEGO.MINIJUEGO_DINERO WHERE nombre = %s"
        cursor.execute(query,(minijuego,))

        resultado = cursor.fetchone()

        return resultado["descripcion"] if resultado else None
    
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
#                                                      ENDPOINTS OBJETO
# =================================================================================================================================================
# =================================================================================================================================================
# ---------------------------------------------------------
@router.get("/juego/precio_objeto/{nombre}", response_model=int)
def get_precio_objeto(nombre: str):
    precio = obtener_precio_objeto_db(nombre)
    if precio is None:
        raise HTTPException(status_code=404, detail="Objeto no encontrado")
    return precio

def obtener_obj_ruleta():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT nombre FROM JUEGO.OBJ_RULETA"
        cursor.execute(query,(minijuego,))

        resultado = cursor.fetcall()

        return [fila[0] for fila in resultado]
    
    except psycopg2.IntegrityError as e:
        conn.rollback() 
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()
        