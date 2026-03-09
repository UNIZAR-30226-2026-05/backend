from schemas import UsuarioPublico, UsuarioRegistro, MinijuegoInfo 
from database import get_db_connection

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from security import verificar_password, crear_token_acceso, obtener_hash_password, SECRET_KEY, ALGORITHM
from datetime import datetime
from typing import List
import psycopg2
import jwt
from jwt import InvalidTokenError

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# =================================================================================================================================================
# =================================================================================================================================================
#                                                      ENDPOINTS USUARIOS
# =================================================================================================================================================
# =================================================================================================================================================

# ---------------------------------------------------------
# INSERTAR 1 USUARIO (POST)
# ---------------------------------------------------------
#Response model es el modelo de salida también definidio en pydantic
@router.post("/registro/", response_model=UsuarioPublico, status_code=status.HTTP_201_CREATED) 
def crear_usuario(usuario: UsuarioRegistro):  #USuarioREgisrado es la clase de pydantic
    """
    Crea un nuevo usuario en el sistema.

    - **nombre**: nombre único del usuario
    - **password**: contraseña del usuario

    Devuelve la información pública del usuario creado, es decir, su nombre.
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()

    hashed_password = obtener_hash_password(usuario.password) # Hasheamos la contraseña antes de guardarla
    
    try:
        # HAY qeu especificar esquema y tabla
        query = """
            INSERT INTO USUARIOS.USUARIO (nombre, password) 
            VALUES (%s, %s) 
            RETURNING nombre;
        """
        # Ejecutamos la query pasando los datos como tupla (para no inyección)
        cursor.execute(query, (usuario.nombre, hashed_password))
        
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
@router.get("/{nombre_user}/amigos", response_model=List[UsuarioPublico])
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

# =================================================================================================================================================
# =================================================================================================================================================
#                                                      ENDPOINTS SESIÓN ACTIVA
# =================================================================================================================================================
# =================================================================================================================================================

# ---------------------------------------------------------
# IMPORTANTE!! ESto es lo que utilizamos como dependencia en el resto de endpoints para que los usuarios
# necesiten autenticación para utilizarlos.
# Básicamente al llamar a un endpoint como el de unirnos a partida, llama previamente a esta función que comprueba 
# nuestro token en la db y si funciona devuelve el nombre de usuario
# ---------------------------------------------------------
def obtener_usuario_actual(token = Depends(oauth2_scheme)):
    """Valida el token y devuelve el nombre del usuario logueado"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT token FROM USUARIOS.SESION_ACTIVA WHERE usuario = %s", (username,))
        sesion = cursor.fetchone()
        
        if not sesion or sesion['token'] != token: 
            raise credentials_exception
            
        return username # Devuelve el nombre del usuario verificado
    finally:
        cursor.close()
        conn.close()



# ---------------------------------------------------------
#  CREAR UNA NUEVA SESIÓN ACTIVA AL HACER LOGIN USUARIO (POST)
# ---------------------------------------------------------
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    #en form_data está username y password
    conn = get_db_connection()
    cursor = conn.cursor()
    
    form_data

    try:
        # Buscar al usuario en la tabla USUARIOS.USUARIO
        cursor.execute("SELECT nombre, password FROM USUARIOS.USUARIO WHERE nombre = %s", (form_data.username,))
        usuario = cursor.fetchone()

        #En database.py, hemos utilizaodo RealDictCursor, que devuelve un diccionario , luego en usuario se 
        # almacena {'nombre': '...', 'password': 'hash...'}
        
        # Verificar si existe y si la contraseña coincide con el hash
        if not usuario or not verificar_password(form_data.password, usuario['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos",
            )
        
        # SI LA CONTRASEÑA ES CORRECTA:
        # Crear el token JWT
        access_token = crear_token_acceso(data={"sub": usuario['nombre']})
        
        # Guardar o actualizar la sesión en USUARIOS.SESION_ACTIVA
        query = """
            INSERT INTO USUARIOS.SESION_ACTIVA (usuario, token, ult_acceso)
            VALUES (%s, %s, %s)
            ON CONFLICT (usuario) 
            DO UPDATE SET token = EXCLUDED.token, ult_acceso = EXCLUDED.ult_acceso;
        """
        cursor.execute(query, (usuario['nombre'], access_token, datetime.now()))
        conn.commit()
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    finally:
        cursor.close()
        conn.close()
