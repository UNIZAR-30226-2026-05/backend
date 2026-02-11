#IMporta routers y los registra (app.include_router(usuarios.router))

from fastapi import FastAPI

app = FastAPI()  # Esta es la variable que busca Uvicorn

@app.get("/")
def read_root():
    return {"Hello": "World"}