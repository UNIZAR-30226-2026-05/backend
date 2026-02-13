from schemas import UsuarioPublico, UsuarioRegistro, MinijuegoInfo 
from database import get_db_connection

from fastapi import APIRouter, HTTPException, status
from typing import List
import psycopg2

router = APIRouter()


# =================================================================================================================================================
# =================================================================================================================================================
#                                                      ENDPOINTS USUARIOS
# =================================================================================================================================================
# =================================================================================================================================================

# ---------------------------------------------------------
# INSERTAR 1 USUARIO (POST)
# ---------------------------------------------------------
#Response model es el modelo de salida también definidio en pydantic
@router.post("/", response_model=UsuarioPublico, status_code=status.HTTP_201_CREATED) 
def crear_usuario(usuario: UsuarioRegistro):  #USuarioREgisrado es la clase de pydantic
    """
    Crea un nuevo usuario en el sistema.

    - **nombre**: nombre único del usuario
    - **password**: contraseña del usuario

    Devuelve la información pública del usuario creado, es decir, su nombre.
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # HAY qeu especificar esquema y tabla
        query = """
            INSERT INTO USUARIOS.USUARIO (nombre, password) 
            VALUES (%s, %s) 
            RETURNING nombre;
        """
        # Ejecutamos la query pasando los datos como tupla (para no inyección)
        cursor.execute(query, (usuario.nombre, usuario.password))
        
        # Confirmamos los cambios en la BD -> ESto es sobre todo cuando vas cogiendo muchos datos para que se te guarden pero no es imprescindible
        conn.commit()
        
        # COgemos el dato 
        nuevo_usuario = cursor.fetchone() 
        
        return nuevo_usuario # Pydantic filtrará el password automáticamente
        
    except psycopg2.IntegrityError:
        conn.rollback() #  deshacer si hay error
        raise HTTPException(status_code=400, detail="El usuario ya existe")
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cursor.close()
        conn.close()

# ---------------------------------------------------------
# LEER TODOS USERS (GET)
# ---------------------------------------------------------
@router.get("/", response_model=List[UsuarioPublico])
def obtener_todos_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT nombre FROM USUARIOS.USUARIO"
        cursor.execute(query)
        
        resultado = cursor.fetchall() # Trae TODOS
        
        if not resultado:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        return resultado
        
    finally:
        cursor.close()
        conn.close()

# ---------------------------------------------------------
# LEER UNO (GET)
# ---------------------------------------------------------
@router.get("/{nombre}", response_model=UsuarioPublico)
def obtener_usuario(nombre: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT nombre FROM USUARIOS.USUARIO WHERE nombre = %s"
        cursor.execute(query, (nombre,))
        
        resultado = cursor.fetchone() # Trae SOLO UNO
        
        if not resultado:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        return resultado
        
    finally:
        cursor.close()
        conn.close()


# =================================================================================================================================================
# =================================================================================================================================================
#                                                      ENDPOINTS AMIGOS
# =================================================================================================================================================
# =================================================================================================================================================

# ---------------------------------------------------------
# LEER TODOS AMIGOS DE UN USER (GET)
# ---------------------------------------------------------
@router.get("/{nombre_user}", response_model=List[UsuarioPublico])
def obtener_todos_amigos_user(nombre_user: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
        (SELECT usuario1 AS nombre
        FROM USUARIOS.AMIGOS 
        WHERE usuario2 = %s)
        
        UNION
        
        (SELECT usuario2 AS nombre
        FROM USUARIOS.AMIGOS 
        WHERE usuario1 = %s)
    """

        cursor.execute(query, (nombre_user, nombre_user))
        
        resultado = cursor.fetchall() # Trae TODOS
        
        if not resultado:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        return resultado
        
    finally:
        cursor.close()
        conn.close()



"""ESTE ES DE MINIJUEGOS PERO PARA QUE VEAIS QUE CUANDO DEVUELVE LISTA HAY QUE PONER EL FETCHALL Y TIPO LISTA"""
# ---------------------------------------------------------
# LEER VARIOS (GET) 
# ---------------------------------------------------------
@router.get("/juegos/", response_model=List[MinijuegoInfo])
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
