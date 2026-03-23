from fastapi import WebSocket
from routers.usuarios import *

class SessionManager:
    def __init__(self):
        # Diccionario para guardar { "nombre_usuario": WebSocket }
        self.active_users: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.active_users[player_id] = websocket
        # Avisamos a sus amigos de que está online
        await self.broadcast_status_to_friends(player_id, "online")

    async def disconnect(self, player_id: str):
        if player_id in self.active_users:
            del self.active_users[player_id]
            # Al desconectarse, avisamos a sus amigos
            await self.broadcast_status_to_friends(player_id, "offline")

    async def send_personal_message(self, target_player_id: str, message: dict):
        """Envía un mensaje directo a un usuario (ej. una invitación)"""
        if target_player_id in self.active_users:
            websocket = self.active_users[target_player_id]
            await websocket.send_json(message)

    def is_user_online(self, player_id: str) -> bool:
        return player_id in self.active_users

    async def broadcast_status_to_friends(self, user: str, status: str):

        amigos = obtener_todos_amigos_user(user)
        
        for amigo in amigos:
            friend_id = amigo['nombre'] 
            
            if self.is_user_online(friend_id):
                # Le enviamos el aviso
                await self.send_personal_message(friend_id, {
                    "type": "friend_status_update",
                    "friend_id": user,
                    "status": status # "online" u "offline"  
                })



# Instancia global para usar en tus rutas
lobby_manager = SessionManager()