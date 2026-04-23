from fastapi import WebSocket, WebSocketDisconnect
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
        invitaciones_pendientes = obtener_invitaciones_usuario(player_id)

        await self.send_personal_message(player_id, {
            "type": "friend_requests_list",
            "lista": invitaciones_pendientes
        })
        
    async def disconnect(self, player_id: str):
        if player_id in self.active_users:
            del self.active_users[player_id]
            if player_id in self.state_users:
                del self.state_users[player_id]
            # Al desconectarse, avisamos a sus amigos
            await self.broadcast_status_to_friends(player_id, "offline")

    async def send_personal_message(self, target_player_id: str, message: dict):
        """Envía un mensaje directo a un usuario si está conectado"""
        if target_player_id in self.active_users:
            websocket = self.active_users[target_player_id]
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                await self.disconnect(target_player_id)

    def is_user_online(self, player_id: str):
        return player_id in self.active_users
    
    async def start_game(self, player_id: str):
        if player_id in self.state_users:
            self.state_users[player_id] = "in_game"

    async def broadcast_status_to_friends(self, user: str, status: str):
        amigos = obtener_todos_amigos_user(user) 
        
        for amigo in amigos:
            friend_id = amigo['nombre'] 
            if self.is_user_online(friend_id):
                await self.send_personal_message(friend_id, {
                    "type": "friend_status_update",
                    "friend_id": user,
                    "status": status 
                })
                
    async def process_action(self, user: str, action: str, payload: dict = None):
        if payload is None:
            payload = {}

        match action:
            case "invite_friend":
                target_friend = payload.get("friend_id")
                game_id_to_join = payload.get("game_id") 
                
                if target_friend and self.is_user_online(target_friend):
                    await self.send_personal_message(target_friend, {
                        "type": "receive_invite",
                        "from_user": user,
                        "game_id": game_id_to_join
                    })
                else:
                    await self.send_personal_message(user, {"error": "El usuario no está conectado"})
            case "accept_invite":
                target_friend = payload.get("friend_id")
                game_id_to_join = payload.get("game_id") 

            case "get_online_friends":
                amigos_db = obtener_todos_amigos_user(user)
                
                amigos_conectados = [
                    amigo['nombre'] for amigo in amigos_db 
                    if self.is_user_online(amigo['nombre'])
                ]
                
                await self.send_personal_message(user, {
                    "type": "online_friends_list",
                    "payload": {
                        "friends": amigos_conectados
                    }
                })

            case "send_request":
                target_player = payload.get("player_id")
                list_payers = obtener_todos_usuarios()

                if target_player not in list_payers:
                    await self.send_personal_message(user, {
                        "type": "user_not_exists",
                        "username": target_player 
                    })
                    return 

                check = enviarSolicitud(user, target_player)
                if check:
                    await self.send_personal_message(user, {
                        "type": "request_sended",
                        "username": target_player 
                    })
                else:
                    await self.send_personal_message(user, {
                        "type": "failed_request",
                        "username": target_player, 
                        "cause": "Ya son amigos"   
                    })

            case "accept_request":
                target_player = payload.get("player_id")
                aceptarSolicitud(target_player, user)

            case "reject_request":
                target_player = payload.get("player_id")
                rechazarSolicitud(target_player, user)

lobby_manager = SessionManager()