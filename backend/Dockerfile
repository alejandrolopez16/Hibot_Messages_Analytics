FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema mínimas para bcrypt y cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
  && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python primero (capa cacheada si requirements no cambia)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY app/ app/

# Cloud Run inyecta PORT=8080; se usa como variable de entorno en CMD
ENV PORT=8080

# 0.0.0.0 obligatorio para que Cloud Run enrute el tráfico al contenedor
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
