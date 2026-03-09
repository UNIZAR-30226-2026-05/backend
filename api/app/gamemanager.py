
# Controla todos los juegos activos que hay actualmente y se encarga de anunciar
# a los jugadores que estan esperando que ha iniciado la partida

from fastapi import WebSocket

# Crea una nueva sesion de juego. Nunca se llama directamente a esta sino a GameConnectionManager
# el cual se encargara de que si no existe crear uno nuevo

class GameSession:
        def __init__(self, game_id: str):
            self.game_id = game_id
            self.players: dict[str, WebSocket] = {}
            self.status = "WAITING"
            self.boar_state = {}
        
        @property
        def is_full(self):
            return len(self.palyers) == 4
        
        async def broadcast (self, message: dict):
            for ws in self.players.values():
                await ws.send_json(message)

class GameConnectionManager:
    def __init__(self):
        self.sessions: dict[str, GameSession] = {}

    async def connect(self, websocket: WebSocket, game_id: str, player_id: str):
        await websocket.accept()

        if game_id not in self.sessions:
            self.sessions[game_id] = GameSession(game_id)
        
        session = self.sessions[game_id]

        if session.is_full or session.status != "WAITING":
            await websocket.send_json({"error: La partida esta llena"})
            await websocket.close()
            return False
        session.players[player_id] = websocket

        await session.broadcast({
            "type" : "lobby_update",
            "players_connected": len(session.players),
            "message": f"Jugador {player_id} se ha unido"
        })

        if session.is_full:
            session.status = "PLAYING"
            await session.broadcast({
                "type": "game_start",
                "message": "Empieza el juego"
            })
        return True

manager = GameConnectionManager()