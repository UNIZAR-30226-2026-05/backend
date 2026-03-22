# Recibe la conexion, valida el mensaje y se lo pasa a gamemanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from gamemanager import manager
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