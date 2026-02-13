#IMporta routers y los registra (app.include_router(usuarios.router))

from fastapi import FastAPI
from routers import usuarios

app = FastAPI()  # Esta es la variable que busca Uvicorn

# Conectamos el archivo usuarios.py al sistema principal
app.include_router(
    usuarios.router,       # El objeto 'router' de usuarios.py
    prefix="/usuarios",    # Todas las rutas empezarán por /usuarios
    tags=["Esquema de usuarios"]      # Título para la documentación
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

