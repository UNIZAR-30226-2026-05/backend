import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from unittest.mock import patch, MagicMock

# Usa una ruta consistente para todos
from gamemanager import manager, GameSession
from sessionmanager import lobby_manager
from api.app.main import app 
# O "from main import app" si el archivo main está en la raíz

# Instanciación del cliente de pruebas de FastAPI
client = TestClient(app)

# Contador global para game_ids únicos
_game_id_counter = 0

def _get_unique_game_id():
    global _game_id_counter
    _game_id_counter += 1
    return str(_game_id_counter)

# ==============================================================================
# FIXTURES DE SEGURIDAD Y ESTADO (MOCKING AVANZADO)
# ==============================================================================

class AnyString(str):
    """
    Clase auxiliar de inyección (Wildcard Matcher). 
    Sobreescribe los métodos de comparación mágica para que devuelva True 
    ante cualquier comparación (ej: sesion['token'] != token).
    """
    def __eq__(self, other): return True
    def __ne__(self, other): return False

@pytest.fixture(autouse=True)
def setup_entorno_websockets():
    """
    Limpia la memoria del servidor antes  de cada test y simula la capa 
    de seguridad (JWT y PostgreSQL) para permitir 
    la conexión del TestClient sin dependencias.
    """
    # 1. Purgado de estado ANTES (Evita la contaminación cruzada entre tests)
    # Limpiamos todas las conexiones existentes
    for game_id in list(manager.active_games.keys()):
        session = manager.active_games[game_id]
        session.players.clear()
    
    lobby_manager.active_users.clear()
    lobby_manager.state_users.clear()
    manager.active_games.clear()
    
    # Inyección de dependencias para la fase de Handshake
    with patch("routers.websocket.jwt.decode") as mock_jwt, \
         patch("routers.websocket.get_db_connection") as mock_db, \
         patch("gamemanager.existe_partida", return_value=True), \
         patch("gamemanager.jugador_en_partida", return_value=True), \
         patch("sessionmanager.obtener_invitaciones_usuario", return_value=[]), \
         patch("sessionmanager.obtener_todos_amigos_user", return_value=[]), \
         patch("sessionmanager.obtener_todos_usuarios", return_value=["Edu1", "Edu2"]), \
         patch("sessionmanager.enviarSolicitud", return_value=True), \
         patch("sessionmanager.aceptarSolicitud", return_value=True), \
         patch("sessionmanager.rechazarSolicitud", return_value=True), \
         patch("gamemanager.obtenerTipoCasilla", return_value=("normal", 0)), \
         patch("gamemanager.tirarDados", return_value=(2, 3, 5)), \
         patch("gamemanager.eliminar_jugador_partida", return_value=True), \
         patch("gamemanager.actualizar_casilla", return_value=True),\
         patch("gamemanager.obtener_precio_objeto_db", return_value=1 ):

         # El token simulado será directamente el nombre del usuario
         mock_jwt.side_effect = lambda token, *args, **kwargs: {"sub": token}
         
         # Mock de cursor para la verificación de sesión en la tabla SESION_ACTIVA
         mock_cursor = MagicMock()
         mock_cursor.fetchone.return_value = {"token": AnyString()}
         mock_db.return_value.cursor.return_value = mock_cursor
         
         yield
    
    # 2. Purgado de estado DESPUÉS (Limpieza post-test)
    for game_id in list(manager.active_games.keys()):
        session = manager.active_games[game_id]
        session.players.clear()
    
    lobby_manager.active_users.clear()
    lobby_manager.state_users.clear()
    manager.active_games.clear()

@pytest.fixture
def partida_en_espera():
    game_id = _get_unique_game_id()
    
    sesion = GameSession(game_id=game_id)
    sesion.status = "WAITING"
    
    manager.active_games[game_id] = sesion
    return game_id, "Edu1"

@pytest.fixture
def partida_en_espera2():
    game_id = _get_unique_game_id()
    
    sesion = GameSession(game_id=game_id)
    sesion.status = "WAITING"
    
    manager.active_games[game_id] = sesion
    return game_id, "Aritz1"
# ==============================================================================
# FUNCIONES AUXILIARES DE CONTROL DE FLUJO ASÍNCRONO
# ==============================================================================

def esperar_evento(ws, tipo_esperado: str, max_intentos: int = 10, timeout: float = 5.0) -> dict:
    print(f"\n[DEBUG] Esperando evento: {tipo_esperado}")
    import time
    start_time = time.time()
    
    for i in range(max_intentos):
        try:
            if time.time() - start_time > timeout:
                pytest.fail(f"Timeout esperando {tipo_esperado} (>{timeout}s)")
            
            mensaje = ws.receive_json()
            
            if mensaje is None:
                print(f"[DEBUG] Intento {i+1}: Conexión cerrada (recibió None)")
                pytest.fail(f"Conexión cerrada mientras se esperaba {tipo_esperado}")
            
            print(f"[DEBUG] Intento {i+1}: Recibido {mensaje.get('type')}")
            
            if mensaje.get("type") == tipo_esperado:
                return mensaje
        except Exception as e:
            print(f"[DEBUG] Error en la conexión: {e}")
            pytest.fail(f"Error esperando {tipo_esperado}: {e}")
    
    pytest.fail(f"Bloqueo detectado buscando {tipo_esperado} (intentos agotados)")

# ==============================================================================
# TESTS DE WEBSOCKETS GAMEMANAGER
# ==============================================================================

def test_ws_conexion_partida_sin_token():
    """
    Prueba Negativa: Intento de conexión sin JWT.
    Verifica el rechazo a nivel de protocolo (Status 1008/403).
    """
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/partida/1") as ws:
            ws.receive_json()

def test_ws_conexion_exitosa_partida(partida_en_espera):
    """
    Conexión exitosa al entorno de Lobby.
    Evalúa la correcta instanciación del pipeline de inicialización del jugador.
    """
    game_id, player_id = partida_en_espera
    
    with client.websocket_connect(f"/ws/partida/{game_id}?token={player_id}") as ws:
        respuesta = esperar_evento(ws, "lobby_update")
        assert "players_connected" in respuesta
        assert player_id in respuesta["players_connected"]

def test_ws_accion_mover_jugador(partida_en_espera):
    game_id, _ = partida_en_espera
    
    # Necesitas 4 tokens/nombres distintos
    jugadores = ["Edu1", "Edu2", "Edu3", "Edu4"]
    
    # Usamos un ExitStack para manejar 4 conexiones al mismo tiempo fácilmente
    from contextlib import ExitStack
    
    with ExitStack() as stack:
        # Conectamos a los 4 jugadores
        websockets = [
            stack.enter_context(client.websocket_connect(f"/ws/partida/{game_id}?token={n}"))
            for n in jugadores
        ]
        
        # El manager ya debería haber generado los dados automáticamente al llegar el 4º
        ws1 = websockets[0]
        ws1.send_json({"action": "move_player"})
        
        # Ahora el evento 'player_moved' sí debería llegar porque hay dados en la lista
        respuesta = esperar_evento(ws1, "player_moved")
        assert respuesta is not None
        assert respuesta["user"] == "Edu1"


def test_ws_accion_comprar_objeto(partida_en_espera):
    game_id, _ = partida_en_espera
    jugadores = ["Edu1", "Edu2"]

    from contextlib import ExitStack

    with ExitStack() as stack:
        websockets = [
            stack.enter_context(client.websocket_connect(f"/ws/partida/{game_id}?token={n}"))
            for n in jugadores
        ]

        ws1 = websockets[0]

        ws1.send_json({
            "action": "comprar_objeto",
            "payload": {"objeto": "Avanzar Casillas"}
        })

        respuesta_saldo = esperar_evento(ws1, "balances_changed")
        assert respuesta_saldo["balances"]["Edu1"] == 0

        respuesta_inventario = esperar_evento(ws1, "inventory_updated")
        assert respuesta_inventario["user"] == "Edu1"
        assert respuesta_inventario["objeto_obtenido"] == "Avanzar Casillas"
        assert "Avanzar Casillas" in respuesta_inventario["inventario_actual"]
    


def test_ws_accion_fin_de_turno(partida_en_espera2): # <--- Usa la fixture
    game_id, player_id = partida_en_espera2 # game_id será "1"
    
    jugadores = ["Aritz1", "Aritz2", "Aritz3", "Aritz4"]
    
    # Usamos un ExitStack para manejar 4 conexiones al mismo tiempo fácilmente
    from contextlib import ExitStack
    
    with ExitStack() as stack:
        # Conectamos a los 4 jugadores
        websockets = [
            stack.enter_context(client.websocket_connect(f"/ws/partida/{game_id}?token={n}"))
            for n in jugadores
        ]
        
        # Inicializamos lo necesario para el test
        ws1 = websockets[0]
        ws1.send_json({"action": "end_round"})
        
        respuesta = esperar_evento(ws1, "turn_changed")
        assert sesion.board_state["turn"] == "Aritz2"

def test_ws_penalizacion_barrera(partida_en_espera): # <--- Usa la fixture
    game_id, player_id = partida_en_espera
    
    with client.websocket_connect(f"/ws/partida/{game_id}?token={player_id}") as ws:
        sesion = manager.active_games[game_id]
        
        # Inicializamos el diccionario de penalizaciones si no existe
        if "penalty_turns" not in sesion.board_state:
            sesion.board_state["penalty_turns"] = {}
            
        sesion.board_state["penalty_turns"][player_id] = 2
        
        ws.send_json({"action": "move_player"})
        
        respuesta = ws.receive_json()
        assert "error" in respuesta

# ==============================================================================
# TESTS DE WEBSOCKETS SESION
# ==============================================================================

#def test_ws_conexion_sesion_sin_token():
    """
    Prueba Negativa: Intento de conexión sin JWT.
    Verifica el rechazo a nivel de protocolo (Status 1008/403).
    """
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/usuario/Edu1") as ws:
            ws.receive_json()

#def test_ws_conexion_sesion():
    """
    Prueba Negativa: Intento de conexión sin JWT.
    Verifica el rechazo a nivel de protocolo (Status 1008/403).
    """

    with client.websocket_connect("/ws/usuario/Edu1?token=Edu1") as ws:
        repuesta = esperar_evento(ws,"friend_requests_list" )
        assert "lista" in repuesta

#def test_ws_accion_get_online_friends():
    """
    Prueba sobre WS: Acción 'get_online_friends'.
    """
    with client.websocket_connect("/ws/usuario/Edu1?token=Edu1") as ws:
        # Emitimos la instrucción
        ws.send_json({"action": "get_online_friends"})
        
        # Validamos el callback
        respuesta = esperar_evento(ws, "online_friends_list")
        assert "friends" in respuesta


#def test_ws_accion_send_request_usuario_inexistente():
    """
    Prueba Negativa: 
    Intento de agregación de un usuario no existente.
    """
    with client.websocket_connect("/ws/usuario/Edu?token=Edu1") as ws:
        ws.send_json({
            "action": "send_request", 
            "payload": {
                "player_id": "UsuarioFantasma"
            }
        })
        
        respuesta = esperar_evento(ws, "user_not_exists")
        assert respuesta["username"] == "UsuarioFantasma"

#def test_ws_accion_send_request_usuario_conectado():
    """
    Intento de agregación de un usuario conectado en el momento.
    """
    with client.websocket_connect("/ws/usuario/Edu1?token=Edu1") as ws1:
        with client.websocket_connect("/ws/usuario/Edu2?token=Edu2") as ws2:
            ws1.send_json({
                "action": "send_request", 
                "payload": {"player_id": "Edu2"}
            })
            
            respuesta1 = esperar_evento(ws1, "request_sended")
            assert respuesta1["username"] == "Edu2"
            respuesta2 = esperar_evento(ws2, "new_friend_request")
            assert respuesta2["from_user"] == "Edu1"

#def test_ws_accion_send_request_ya_amigos():
    """
    Intento de agregación de un usuario conectado en el momento.
    """
    def test_ws_accion_send_request_ya_amigos():
        with client.websocket_connect("/ws/usuario/Edu1?token=Edu1") as ws1:
            with client.websocket_connect("/ws/usuario/Edu2?token=Edu2") as ws2:
            # Usamos side_effect para que la 1ª vez funcione y la 2ª falle
                with patch("sessionmanager.enviarSolicitud", side_effect=[True, False]):
                    
                    ws1.send_json({"action": "send_request", "payload": {"player_id": "Edu2"}})
                    
                    esperar_evento(ws1, "request_sended")
                    esperar_evento(ws2, "new_friend_request")

                    ws2.send_json({"action": "accept_request", "payload": {"player_id": "Edu1"}})

                    ws1.send_json({"action": "send_request", "payload": {"player_id": "Edu2"}})

                    # Ahora la cola de ws1 solo debería tener el nuevo mensaje
                    respuesta = esperar_evento(ws1, "failed_request")
                    assert respuesta["username"] == "Edu2"
                

#def test_ws_accion_invite_friend_real():
    """
    Valida el envio correcto de invitaciones a partida
    """
    # Edu2 se conecta para recibir la invitación
    with client.websocket_connect("/ws/usuario/Edu2?token=Edu2") as ws_edu2:
        # Edu1 se conecta para enviarla
        with client.websocket_connect("/ws/usuario/Edu1?token=Edu1") as ws_edu1:
            ws_edu1.send_json({
                "action": "invite_friend",
                "payload": {"friend_id": "Edu2", "game_id": 99}
            })
            
            respuesta = esperar_evento(ws_edu2, "receive_invite")
            assert respuesta["from_user"] == "Edu1"
            assert respuesta["game_id"] == 99

