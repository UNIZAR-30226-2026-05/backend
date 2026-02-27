from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Diccionario que guarda: { id_partida: [lista_de_websockets] }
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, partida_id: int):
        await websocket.accept()
        if partida_id not in self.active_connections:
            self.active_connections[partida_id] = []
        self.active_connections[partida_id].append(websocket)

    def disconnect(self, websocket: WebSocket, partida_id: int):
        if partida_id in self.active_connections:
            self.active_connections[partida_id].remove(websocket)

    async def broadcast_to_room(self, partida_id: int, message: dict):
        if partida_id in self.active_connections:
            for connection in self.active_connections[partida_id]:
                await connection.send_json(message)

manager = ConnectionManager()