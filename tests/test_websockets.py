import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from unittest.mock import patch, MagicMock

# Usa una ruta consistente para todos
from api.app.gamemanager import manager, GameSession
from api.app.sessionmanager import lobby_manager
from api.app.main import app 
# O "from main import app" si el archivo main está en la raíz

# Instanciación del cliente de pruebas de FastAPI
client = TestClient(app)

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
    # 1. Purgado de estado (Evita la contaminación cruzada entre tests)
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
         patch("gamemanager.obtener_precio_objeto_db", return_value=100), \
         patch("gamemanager.obtenerTipoCasilla", return_value=("normal", 0)), \
         patch("gamemanager.tirarDados", return_value=(2, 3, 5)), \
         patch("gamemanager.eliminar_jugador_partida", return_value=True), \
         patch("gamemanager.actualizar_casilla", return_value=True):

         # El token simulado será directamente el nombre del usuario
         mock_jwt.side_effect = lambda token, *args, **kwargs: {"sub": token}
         
         # Mock de cursor para la verificación de sesión en la tabla SESION_ACTIVA
         mock_cursor = MagicMock()
         mock_cursor.fetchone.return_value = {"token": AnyString()}
         mock_db.return_value.cursor.return_value = mock_cursor
         
         yield

@pytest.fixture
def partida_en_espera():
    """Crea una partida con estructura inicial en el manager."""
    from api.app.gamemanager import GameSession
    game_id = "1"
    player_id = "Edu1"
    
    # Configuramos el objeto
    sesion = GameSession(game_id=game_id)
    sesion.status = "WAITING"
    sesion.board_state["order"] = {player_id: 1}
    sesion.board_state["positions"] = {player_id: 0}
    sesion.board_state["balances"] = {player_id: 1000}
    
    # La metemos en el manager
    manager.active_games[game_id] = sesion
    
    return game_id, player_id

# ==============================================================================
# FUNCIONES AUXILIARES DE CONTROL DE FLUJO ASÍNCRONO
# ==============================================================================

def esperar_evento(ws, tipo_esperado: str, max_intentos: int = 10) -> dict:
    print(f"\n[DEBUG] Esperando evento: {tipo_esperado}")
    for i in range(max_intentos):
        try:
            mensaje = ws.receive_json()
            print(f"[DEBUG] Intento {i+1}: Recibido {mensaje.get('type')}")
            
            if mensaje.get("type") == tipo_esperado:
                return mensaje
        except Exception as e:
            print(f"[DEBUG] Error en la conexión: {e}")
            break
    pytest.fail(f"Bloqueo detectado buscando {tipo_esperado}")

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
    game_id, player_id = partida_en_espera

    with client.websocket_connect("/ws/partida/{game_id}?token={player_id}") as ws1:
        
        ws1.send_json({"action": "move_player", "dice_result": 5})
        
        respuesta = esperar_evento(ws1, "player_moved")
        assert respuesta["user"] == "Edu1"

def test_ws_accion_comprar_objeto():
    """
    Prueba de Transacción Económica en memoria.
    Evalúa la reducción de saldo vinculada a la compra de un objeto.
    """
    with client.websocket_connect("/ws/partida/4?token=Edu1") as ws1:
        sesion = manager.active_games["4"]
        sesion.board_state["turn"] = "Edu1"
        if "balances" not in sesion.board_state:
            sesion.board_state["balances"] = {}
        sesion.board_state["balances"]["Edu1"] = 1000  
        
        ws1.send_json({
            "action": "comprar_objeto", 
            "objeto": "barrera"
        })
        
        respuesta = esperar_evento(ws1, "inventory_updated")
        assert respuesta["user"] == "Edu1"
        assert respuesta["objeto_obtenido"] == "barrera"

def test_ws_accion_fin_de_turno():
    """
    Verifica que se pase bien de turno.
    """
    with client.websocket_connect("/ws/partida/5?token=Edu1") as ws1:
        sesion = manager.active_games["5"]
        sesion.players["Edu2"] = None 
        sesion.board_state["turn"] = "Edu1"
        sesion.board_state["order"] = {"Edu1": 1, "Edu2": 2}
        
        ws1.send_json({"action": "end_round"})
        
        respuesta = esperar_evento(ws1, "turn_changed")
        assert sesion.board_state["turn"] == "Edu2"

def test_ws_penalizacion_barrera():
    """
    NUEVO: Verifica que un jugador bloqueado no puede mover.
    """
    with client.websocket_connect("/ws/partida/10?token=Edu1") as ws:
        sesion = manager.active_games["10"]
        # Simulamos que ya cayó en una barrera
        sesion.board_state["penalty_turns"]["Edu1"] = 2
        
        ws.send_json({"action": "move_player"})
        
        # El servidor debe responder con un error (según tu gamemanager.py:230)
        respuesta = ws.receive_json()
        assert "error" in respuesta
        assert "turnos de penalización" in respuesta["error"]

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

