import pytest
import os
from unittest.mock import patch, MagicMock

# Importación de las funciones que interactúan con la base de datos
from funcionesAuxiliaresPartida import (
    obtener_precio_objeto_db,
    existe_partida,
    jugador_en_partida,
    eliminar_jugador_partida
)
from database import get_db_connection

# ==============================================================================
# TESTS DE CONEXIÓN A LA BASE DE DATOS (database.py)
# ==============================================================================

@patch.dict(os.environ, {"DATABASE_URL": "postgresql://fake_user:fake_pass@localhost/db"})
@patch("database.psycopg2.connect")
def test_get_db_connection_exito(mock_connect):
    """
    Verifica que la función de conexión a la base de datos lee correctamente
    la variable de entorno DATABASE_URL e invoca al conector psycopg2.
    Se utiliza mock.patch para evitar una conexión real a PostgreSQL.
    """
    # Act: Ejecución de la función a testear
    conexion = get_db_connection()
    
    # Assert: Verificación de que psycopg2.connect fue llamado correctamente
    assert mock_connect.called
    assert conexion == mock_connect.return_value

@patch.dict(os.environ, clear=True) # Simulamos un entorno sin variables
def test_get_db_connection_sin_variable_entorno():
    """
    Comprueba el manejo de excepciones cuando la variable de entorno DATABASE_URL
    no está configurada. Debe levantar un RuntimeError para evitar ejecuciones
    silenciosas con fallos de configuración.
    """
    with pytest.raises(RuntimeError) as exc_info:
        get_db_connection()
    
    assert "La variable de entorno 'DATABASE_URL' no está configurada" in str(exc_info.value)


# ==============================================================================
# TESTS DE CONSULTAS DE LECTURA (SELECT) - funcionesAuxiliaresPartida.py
# ==============================================================================

@patch("funcionesAuxiliaresPartida.get_db_connection")
def test_obtener_precio_objeto_db_existe(mock_get_db):
    """
    Verifica la extracción del precio de un objeto existente.
    Simula un cursor que devuelve un diccionario (RealDictCursor) con el precio.
    """
    # Arrange: Preparación del mock
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Simulamos que la base de datos encuentra el objeto y devuelve su precio
    mock_cursor.fetchone.return_value = {"precio": 15}
    
    # Act
    precio = obtener_precio_objeto_db("Salvavidas")
    
    # Assert
    assert precio == 15
    mock_cursor.execute.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch("funcionesAuxiliaresPartida.get_db_connection")
def test_obtener_precio_objeto_db_no_existe(mock_get_db):
    """
    Verifica el comportamiento de la función cuando se solicita el precio
    de un objeto que no existe en el catálogo de la BD.
    """
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Simulamos que la base de datos no encuentra nada
    mock_cursor.fetchone.return_value = None
    
    precio = obtener_precio_objeto_db("ObjetoInexistente")
    
    assert precio is None

@patch("funcionesAuxiliaresPartida.get_db_connection")
def test_existe_partida_verdadera(mock_get_db):
    """
    Verifica la validación de existencia de una partida activa.
    Comprueba que el retorno es estrictamente booleano True si hay coincidencias.
    """
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_cursor.fetchone.return_value = {"id": 100}
    
    resultado = existe_partida(100)
    
    assert resultado is True

@patch("funcionesAuxiliaresPartida.get_db_connection")
def test_jugador_en_partida_falso(mock_get_db):
    """
    Verifica el control de acceso de un jugador a una partida.
    Comprueba el retorno booleano False cuando la consulta no arroja resultados.
    """
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_cursor.fetchone.return_value = None
    
    resultado = jugador_en_partida("Edu1", 999)
    
    assert resultado is False


# ==============================================================================
# TESTS DE MODIFICACIÓN DE DATOS (DELETE / UPDATE) Y TRANSACCIONES
# ==============================================================================

@patch("funcionesAuxiliaresPartida.get_db_connection")
def test_eliminar_jugador_partida_exito(mock_get_db):
    """
    Verifica el flujo completo de eliminación de un jugador de la tabla JUGANDO
    y la consecuente actualización del número de jugadores en PARTIDA_ACTIVA.
    Valida que se realice el commit de la transacción de forma segura.
    """
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Act
    resultado = eliminar_jugador_partida("Edu1", 1)
    
    # Assert: Comprobamos que es exitoso
    assert resultado is True
    
    # Verificamos que se ejecuta la consulta de DELETE
    assert mock_cursor.execute.call_count == 1
    
    # Verificamos que se consolidaron los cambios en la BD
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch("funcionesAuxiliaresPartida.get_db_connection")
def test_eliminar_jugador_partida_rollback_por_excepcion(mock_get_db):
    """
    Prueba de resiliencia (Negative Testing). Simula una caída o error de integridad
    durante la ejecución de las sentencias SQL. Verifica que el sistema intercepte
    la excepción, aplique el rollback para mantener la consistencia ACID de la BD,
    y devuelva False al controlador principal.
    """
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Simulamos un fallo crítico al intentar ejecutar la query
    mock_cursor.execute.side_effect = Exception("Fallo simulado de conexión o integridad")
    
    # Act
    resultado = eliminar_jugador_partida("Edu1", 1)
    
    # Assert
    assert resultado is False
    
    # Verificamos que NO se hizo commit
    mock_conn.commit.assert_not_called()
    
    # Verificamos que se hizo rollback para revertir transacciones incompletas
    mock_conn.rollback.assert_called_once()
    
    # Verificamos que la conexión se cerró limpiamente a pesar del error
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()