import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# instancia de la aplicación FastAPI 
from main import app

# dependencia de seguridad desde su ruta correcta (routers)
from routers.usuarios import obtener_usuario_actual

# cliente de pruebas de FastAPI
client = TestClient(app)

# ==============================================================================
# CONFIGURACIÓN DE DEPENDENCIAS (MOCKS GLOBALES PARA AUTENTICACIÓN)
# ==============================================================================

def override_obtener_usuario_actual():
    """
    Función auxiliar para sobreescribir la dependencia de seguridad.
    Permite simular que las peticiones protegidas provienen de un usuario autenticado
    sin necesidad de generar y validar tokens JWT reales en cada test.
    """
    return "UsuarioTest"

# ==============================================================================
# TESTS DE LA API DE USUARIOS (/usuarios)
# ==============================================================================

@patch("routers.usuarios.get_db_connection")
def test_registro_usuario_exito(mock_get_db):
    """
    Verifica el endpoint POST /usuarios/registro/.
    Caso de éxito (201): Los datos son válidos y el usuario se inserta correctamente.
    """
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Simulamos que el insert en la BD funcionó (rowcount = 1)
    mock_cursor.rowcount = 1
    
    # Simulamos que la BD nos devuelve el nombre del usuario creado
    mock_cursor.fetchone.return_value = {"nombre": "NuevoUsuario"}
    
    response = client.post(
        "/usuarios/registro/", 
        json={"nombre": "NuevoUsuario", "password": "passwordSegura123"}
    )
    
    assert response.status_code == 201
    assert response.json()["nombre"] == "NuevoUsuario"
    mock_conn.commit.assert_called_once()

def test_registro_usuario_validacion_pydantic():
    """
    Prueba Negativa: Verifica que Pydantic bloquea peticiones malformadas
    antes de que lleguen a la lógica de negocio (BD).
    """
    response = client.post(
        "/usuarios/registro/", 
        json={"nombre": "Usr", "password": "123"}
    )
    
    assert response.status_code == 422
    assert "detail" in response.json()

@patch("routers.usuarios.get_db_connection")
@patch("routers.usuarios.verificar_password")
def test_login_usuario_credenciales_invalidas(mock_verificar, mock_get_db):
    """
    Prueba Negativa: Verifica el endpoint de login con contraseña incorrecta.
    Debe retornar un status 401 Unauthorized.
    """
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_cursor.fetchone.return_value = {"nombre": "Edu1", "password": "hash"}
    mock_verificar.return_value = False
    
    response = client.post(
        "/usuarios/login", 
        data={"username": "Edu1", "password": "PasswordIncorrecta"}
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Usuario o contraseña incorrectos"


# ==============================================================================
# TESTS DE LA API DE PARTIDAS (/partidas)
# ==============================================================================

@patch("routers.partidas.get_db_connection")
def test_obtener_partidas_vacio(mock_get_db):
    """
    Verifica el endpoint GET /partidas/.
    Caso Límite: No hay partidas activas en la BD. Debe retornar 404.
    """
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = []
    
    response = client.get("/partidas/")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "No hay partidas activas"

@patch("routers.partidas.get_db_connection")
def test_crear_partida_protegido_sin_token(mock_get_db):
    """
    Prueba de Seguridad: Intento de crear una partida sin estar autenticado.
    Debe ser bloqueado automáticamente por la dependencia Depends.
    """
    response = client.post("/partidas/crear_partida")
    
    assert response.status_code == 401 

@patch("routers.partidas.get_db_connection")
def test_crear_partida_exito(mock_get_db):
    """
    Verifica el endpoint POST /partidas/crear_partida.
    Inyecta una sesión válida para saltar la seguridad y prueba la lógica de negocio.
    """
    app.dependency_overrides[obtener_usuario_actual] = override_obtener_usuario_actual
    
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_cursor.fetchone.return_value = {"id": 5}
    
    response = client.post("/partidas/crear_partida")
    
    assert response.status_code == 201
    assert response.json() == 5
    
    app.dependency_overrides = {}

@patch("routers.partidas.get_db_connection")
@patch("routers.partidas.verificar_usuario")
def test_unirse_partida_llena(mock_verificar_usuario, mock_get_db):
    """
    Prueba de Regla de Negocio: Verifica que el sistema rechaza la conexión si ya tiene 4 jugadores.
    """
    app.dependency_overrides[obtener_usuario_actual] = override_obtener_usuario_actual
    
    mock_conn, mock_cursor = MagicMock(), MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Simulamos que la función verificar_usuario dice que SÍ existe
    mock_verificar_usuario.return_value = True
    
    # Simulamos el orden exacto de las consultas que el endpoint realiza:
    mock_cursor.fetchone.side_effect = [
        {"id": 1},                 # 1ª Consulta: La partida existe
        {"num_jugadores": 4}       # 2ª Consulta: El conteo dice que ya hay 4 jugadores
    ]
    
    response = client.post("/partidas/unirse_partida", json={"id_partida": 1})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "La partida está llena"
    
    app.dependency_overrides = {}


# ==============================================================================
# TESTS DE LA API DE JUEGO (/juego)
# ==============================================================================

@patch("routers.juego.obtener_precio_objeto_db")
def test_get_precio_objeto_exito(mock_obtener_precio):
    """
    Verifica la consulta de precios de la tienda.
    Se mockea directamente la función auxiliar invocada por el endpoint.
    """
    mock_obtener_precio.return_value = 15
    
    response = client.get("/juego/juego/precio_objeto/Salvavidas")
    
    assert response.status_code == 200
    assert response.json() == 15

@patch("routers.juego.obtener_precio_objeto_db")
def test_get_precio_objeto_no_encontrado(mock_obtener_precio):
    """
    Verifica el manejo de errores al solicitar el precio de un objeto inexistente.
    """
    mock_obtener_precio.return_value = None
    
    response = client.get("/juego/juego/precio_objeto/ObjetoFalso")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Objeto no encontrado"