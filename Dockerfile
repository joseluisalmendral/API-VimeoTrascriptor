FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar y instalar las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Cloud Run utiliza la variable de entorno PORT (por defecto 8080)
ENV PORT 8080
EXPOSE 8080

# Comando para iniciar la aplicación con uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
