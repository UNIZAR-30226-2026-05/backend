
# Controla todos los juegos activos que hay actualmente y se encarga de anunciar
# a los jugadores que estan esperando que ha iniciado la partida

from fastapi import WebSocket

# Crea una nueva sesion de juego. Nunca se llama directamente a esta sino a GameConnectionManager
# el cual se encargara de que si no existe crear uno nuevo

class GameSession:
        def __init__(self, game_id: int):
            self.game_id = game_id
            self.players: dict[int, WebSocket] = {}
            self.status = "WAITING"
            self.board_state = {}
        
        @property
        def is_full(self):
            return len(self.players) == 4
        
        async def broadcast (self, message: dict):
            for ws in self.players.values():
                await ws.send_json(message)

class GameManager:
    def __init__(self):
        self.active_games: dict[int, GameSession] = {}

    async def connect(self, websocket: WebSocket, game_id: int, player_id: str):
        await websocket.accept()

        if game_id not in self.active_games:
            self.active_games[game_id] = GameSession(game_id)
        
        session = self.active_games[game_id]

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

    async def disconnect(self, websocket: WebSocket, game_id: int, player_id:str):
        if game.id in self.active_games:
            session = self.active_games[game_id]
            if player_id in session.players:

                session.players[player_id] = None
                await session.broadcast({
                    "type": "player_disconnected",
                    "message": "El jugador"
                })
                
    async def process_action(self, game_id: int, user: str, message: dict):
        session = self.active_games[game_id]
        
        match message["action"]:
            case "tirar_dado":
                dado = 5
                nueva_casilla = session.board_state["posiciones"][user] + dado
                session.board_state["posiciones"][user] = nueva_casilla

                actualizar_casilla(game_id, user, nueva_casilla)

                await session.broadcast({
                    "type": "rolled_dice",
                    "user": user,
                    "result": dado,
                    "nueva_casilla": nueva_casilla
                })
    
manager = GameManager()