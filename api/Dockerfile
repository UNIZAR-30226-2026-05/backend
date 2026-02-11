# imagen base de python ligera
FROM python:3.11-slim

# directorio de trabajo dentro del contenedor
WORKDIR /app

# copiamos al interior del contenedor el fichero de dependencias y ejecutamos comando para instalarlas
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# copiamos todo el código que tenemos en el directorio actual (app)
COPY . .

# comando para arrancar la app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]