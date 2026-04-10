import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise RuntimeError(
            "La variable de entorno 'DATABASE_URL' no está configurada. "
            "Asegúrate de tener un archivo .env o la variable exportada."
        )

    try:
        # psycopg2 permite conectar usando una URL de conexión (DSN)
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor # Devuelve diccionarios
        )
        return conn
    except Exception as e:
        print(f"Error conectando a la BD: {e}")
        raise e