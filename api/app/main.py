#IMporta routers y los registra (app.include_router(usuarios.router))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import usuarios
from routers import juego
from routers import partidas
from routers import websocket

app = FastAPI()  # Esta es la variable que busca Uvicorn

# Bloque de configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  # Permite POST, GET, OPTIONS...
    allow_headers=["*"],
)

# Conectamos el archivo usuarios.py al sistema principal
app.include_router(
    usuarios.router,       # El objeto 'router' de usuarios.py
    prefix="/usuarios",    # Todas las rutas empezarán por /usuarios
    tags=["Esquema de usuarios"]      # Título para la documentación
)

app.include_router(
    juego.router,       # El objeto 'router' de juego.py
    prefix="/juego",    # Todas las rutas empezarán por /juego
    tags=["Esquema de juego"]      # Título para la documentación
)

app.include_router(
   partidas.router,       # El objeto 'router' de partidas.py
    prefix="/partidas",    # Todas las rutas empezarán por /partidas
    tags=["Esquema de partidas"]      # Título para la documentación
)

app.include_router(websocket.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

