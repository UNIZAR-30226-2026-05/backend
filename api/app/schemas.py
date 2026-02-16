#MODELOS PYDANTIC
#sirve validar que lo que te envían está bien y para filtrar lo que devuelves (p ej: no devolver contraseñas)
"""
La verdad es que usar esto es un poco coñazo, pero merece la pena, a la larga te ahorra muchos problemas porque con esto devolvemos
datos como un tipo en concreto definido al ejecutar un endpoint, y sino devolvemos un diccionario a pelo.

por ejemplo, al crear un usuario con el endpoint de crear, sin pydantic hay que meterle todos los ifs en ese endpoint para comprobar si la edad
es un núemero entero, si el nombre no supera x caracteres, si los campos obligaorios están completos... Porque si no haces los ifs se intenta meter
directamente en la base de datos con tipos raros y te da error de bbdd en lugar de la api, q es más difícil resolver.
EL tema es q si usamos pydantic, hace toda esa validación antes de entrar en la función del endpoint, porqeu has fijado como quiers que sea exactamente 
cada campo. OS pongo ejemplo abajo de posibles atributos que se les puede poner, pero hay muchos (obligatorio o opcional, longitud, tipo...)

Además, fastapi ofrece webs condocumentación qeu te muestra de manera muy cómoda los tipos de datos para cada endpoint y tal, es muy visual y lo hace
automáticamente, y coge lo que se ha puesto en los esquemas pydantic asi q renta

"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- MODELOS DE ENTRADA (Lo que el frontend nos envía) ---

class UsuarioRegistro(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=50, example="paquito")
    password: str = Field(..., min_length=6, example="secreto123")

class CrearPartida(BaseModel):
    
    minijuego_inicial: str

# --- MODELOS DE SALIDA (Lo que devolvemos al frontend) ---

class UsuarioPublico(BaseModel):
    nombre: str
    # NO incluimos el password aquí!
    
    class Config:
        from_attributes = True # Esto ayuda a que Pydantic entienda diccionarios

class MinijuegoInfo(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class PersonajesInfo(BaseModel):
    nombre: str = Field(..., example="Banquero")
    habilidad: str = Field(..., example="Robar dinero a tus contrincantes")
    descripcion: str = Field(..., example="Es el personaje que puede controlar...")

class JoinPartida(BaseModel):
    nombre: str