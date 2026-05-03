FROM python:3.11-slim

# Instala bibliotecas de sistema necessárias para o OpenCV
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos (app.py, detector.py, etc)
COPY . .

# Configura a porta padrão do Render
ENV PORT=10000
EXPOSE 10000

# Inicia o servidor usando Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "60", "app:app"]
