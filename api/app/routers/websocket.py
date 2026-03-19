# Recibe la conexion, valida el mensaje y se lo pasa a gamemanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from gamemanager import manager
from schemas import PlayerAction
import traceback

router = APIRouter()

@router.websocket("/ws/partida/{game_id}/{player_id}")
async def game_endpoint(websocket: WebSocket, game_id: str, player_id: str):

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