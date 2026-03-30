from fastapi import WebSocket
from routers.usuarios import *

class SessionManager:
    def __init__(self):
        self.active_users: dict[str, WebSocket] = {}
        self.state_users: dict[str, str] = {}

    async def connect(self, websocket: WebSocket, player_id: str):
        
        self.active_users[player_id] = websocket
        self.state_users[player_id] = "Lobby"
        # Avisamos a sus amigos de que está online
        await self.broadcast_status_to_friends(player_id, "online")
        
    async def disconnect(self, player_id: str):
        if player_id in self.active_users:
            del self.active_users[player_id]
            # Al desconectarse, avisamos a sus amigos
            await self.broadcast_status_to_friends(player_id, "offline")

    async def send_personal_message(self, target_player_id: str, message: dict):
        """Envía un mensaje directo a un usuario (ej. una invitación)"""
        if target_player_id in self.active_users and self.state_users[target_player_id] == "online":
            websocket = self.active_users[target_player_id]
            await websocket.send_json(message)

    def is_user_online(self, player_id: str) -> bool:
        return player_id in self.active_users
    
    async def start_game(self, player_id: str):
        self.state_users[player_id] = "in_game"

    async def broadcast_status_to_friends(self, user: str, status: str):

        amigos = obtener_todos_amigos_user(user)
        
        for amigo in amigos:
            friend_id = amigo['nombre'] 
            
            if self.is_user_online(friend_id):
                # Le enviamos el aviso
                await self.send_personal_message(friend_id, {
                    "type": "friend_status_update",
                    "friend_id": user,
                    "status": status 
                })
                
    async def process_action(self, user: str, action: str, payload: dict = None):
        match action:
            case "invite_friend":
                target_friend = payload.get("friend_id")
                game_id_to_join = payload.get("game_id") 
                
                if target_friend and lobby_manager.is_user_online(target_friend):
                    await lobby_manager.send_personal_message(target_friend, {
                        "action": "receive_invite",
                        "from_user": user,
                        "game_id": game_id_to_join
                    })
                else:
                    await self.send_json({"error": "El usuario no está conectado"})

            case "get_online_friends":
                 # Sacamos los amigos de la BBDD
                amigos_db = obtener_todos_amigos_user(user)
                
                # Filtramos los que están conectados ahora mismo
                amigos_conectados = []
                for amigo in amigos_db:
                    friend_id = amigo['nombre']
                    if lobby_manager.is_user_online(friend_id):
                        amigos_conectados.append(friend_id)
                
                # Se lo enviamos al jugador
                await self.send_json({
                    "action": "online_friends_list",
                    "payload": {
                        "friends": amigos_conectados
                    }
                })


# Instancia global para usar en tus rutas
lobby_manager = SessionManager()