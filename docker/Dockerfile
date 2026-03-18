FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias primero (capa cacheada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorios de datos y logs
RUN mkdir -p data/menus logs

CMD ["python", "automata.py"]
