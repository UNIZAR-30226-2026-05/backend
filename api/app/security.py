from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt

# Configuración JWT
SECRET_KEY = "eduardo_es_el_miembro_mas_guapo_de_todo_el_equipo"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Configuración de Passlib para hashear con Bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def obtener_hash_password(password):
    """Devuelve el hash de una contraseña que recibe"""
    return pwd_context.hash(password)

def verificar_password(plain_password, hashed_password):
    """Compara la contraseña recibida con el hash de la base de datos"""
    return pwd_context.verify(plain_password, hashed_password)

def crear_token_acceso(data: dict) -> str:
    """Genera un JWT con fecha de caducidad"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Crea el token firmado
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt