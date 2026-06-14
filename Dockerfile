FROM python:3.12-slim

# Configurações para Python não gerar arquivos .pyc e não bufferizar logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instala dependências Python e as dependências de sistema do Chromium em uma única camada
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium --with-deps \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# O Cloud Run ignora o HEALTHCHECK do Dockerfile, pois usa Probes próprias, 
# mas mantemos a exposição da porta 8080 (padrão do Cloud Run)
EXPOSE 8080

# No Cloud Run, o app DEVE ouvir na porta definida pela variável $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
