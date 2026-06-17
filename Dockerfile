FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema necesarias para NiceGUI y matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias Python
COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

# Copia el codigo
COPY . .

# Crea el directorio de datos si no existe
RUN mkdir -p data

EXPOSE 8080

CMD ["python", "main.py"]