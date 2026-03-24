# Recibe la conexion, valida el mensaje y se lo pasa a gamemanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from gamemanager import manager
from sessionmanager import lobby_manager
from schemas import PlayerAction
import traceback
import jwt
from security import SECRET_KEY, ALGORITHM
from database import get_db_connection

router = APIRouter()

@router.websocket("/ws/partida/{game_id}") 
async def game_endpoint(websocket: WebSocket, game_id: str, token: str):

    # Validar el token manualmente
    try:
        # Decodificamos el token para sacar el nombre de usuario
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        player_id = payload.get("sub")
        
        if player_id is None:
            await websocket.close(code=1008, reason="Token vacío")
            return

        # Comprobamos en la base de datos que la sesión sigue activa
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM USUARIOS.SESION_ACTIVA WHERE usuario = %s", (player_id,))
        sesion = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not sesion or sesion['token'] != token: 
            await websocket.close(code=1008, reason="Sesión caducada o iniciada en otro sitio")
            return

    except jwt.InvalidTokenError:
        # ERROR DE TOKEN
        await websocket.close(code=1008, reason="Token inválido")
        return
    except Exception as e:
        print(f"Error validando token WS: {e}")
        await websocket.close(code=1011)
        return


    connected = await manager.connect(websocket, game_id, player_id)
    if not connected:
        return
    
    try:
        while True:
            data = await websocket.receive_json()

            try:
                action_data = PlayerAction(**data)

                await manager.process_action(game_id, player_id, action_data.action, action_data.payload)

            except ValidationError:
                await websocket.send_json({"error": "Formato de mensaje invalido"})
            
            except Exception as e:
                print(f"ERROR CRÍTICO EN WS: {e}")
                traceback.print_exc()
                await websocket.send_json({"error": f"Error interno en el servidor: {e}"})

    except WebSocketDisconnect:
        await manager.disconnect(websocket, game_id, player_id)

# ---------------------------------------------
# SESION
# ---------------------------------------------

@router.websocket("/ws/usuario/{user}")
async def active_session(websocket: WebSocket, user: str, token: str):
    # 1. ACEPTAMOS LA CONEXIÓN PRIMERO
    await websocket.accept()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        player_id = payload.get("sub")
        
        if player_id is None:
            await websocket.close(code=1008, reason="Token vacío")
            return
            
        # Comprobamos en la base de datos que la sesión sigue activa
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM USUARIOS.SESION_ACTIVA WHERE usuario = %s", (player_id,))
        sesion = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not sesion or sesion['token'] != token: 
            await websocket.close(code=1008, reason="Sesión caducada o iniciada en otro sitio")
            return
        
    except Exception as e:
        # ¡ESTO ES CRÍTICO PARA SABER QUÉ FALLA!
        print(f"🔥 ERROR en validación de WS para {user}: {e}") 
        await websocket.close(code=1008, reason="Error interno o token inválido")
        return

    # --- 2. CONEXIÓN AL LOBBY ---
    await lobby_manager.connect(websocket, player_id)
    
    # --- 3. BUCLE DE MENSAJES DEL MENÚ ---
    try:
        while True:
            data = await websocket.receive_json()

            try:
                action_data = PlayerAction(**data)
                
                # Gestión de acciones del menú principal
                if action_data.action == "invite_friend":
                    # El jugador quiere invitar a un amigo
                    target_friend = action_data.payload.get("friend_id")
                    game_id_to_join = action_data.payload.get("game_id") # La sala que ha creado
                    
                    if target_friend and lobby_manager.is_user_online(target_friend):
                        # Le mandamos la invitación al amigo
                        await lobby_manager.send_personal_message(target_friend, {
                            "action": "receive_invite",
                            "payload": {
                                "from_user": player_id,
                                "game_id": game_id_to_join
                            }
                        })
                    else:
                        # Opcional: Avisar de que el amigo no está conectado
                        await websocket.send_json({"error": "El usuario no está conectado"})

                elif action_data.action == "get_online_friends":
                    # 1. Sacamos los amigos de la BBDD
                    amigos_db = obtener_todos_amigos_user(player_id)
                    
                    # 2. Filtramos los que están conectados ahora mismo
                    amigos_conectados = []
                    for amigo in amigos_db:
                        friend_id = amigo['nombre']
                        if lobby_manager.is_user_online(friend_id):
                            amigos_conectados.append(friend_id)
                    
                    # 3. Se lo enviamos al jugador
                    await websocket.send_json({
                        "action": "online_friends_list",
                        "payload": {
                            "friends": amigos_conectados
                        }
                    }) 

                else:
                    await websocket.send_json({"error": "Acción no reconocida en el menú"})

            except ValidationError:
                await websocket.send_json({"error": "Formato de mensaje invalido"})
            
            except Exception as e:
                print(f"Error procesando acción del menú: {e}")

    except WebSocketDisconnect:
        # --- 4. DESCONEXIÓN ---
        await lobby_manager.disconnect(player_id)

