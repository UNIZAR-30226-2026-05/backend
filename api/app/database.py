#ESto solo define la función que utilizamos en lso enspoints para conectarnos con la bbdd, no hay que tocar nada

import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="db-postgres",
            database="db",
            user="paquito",
            password="paquito",
            cursor_factory=RealDictCursor # Devuelve diccionarios
        )
        return conn
    except Exception as e:
        print(f"Error conectando a la BD: {e}")
        raise e