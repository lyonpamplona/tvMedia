# Imagem do backend AdSignage (FastAPI + Uvicorn).
FROM python:3.12-slim

# Evita arquivos .pyc e garante logs sem buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Limita o número de arenas do alocador glibc, reduzindo o consumo de RAM
    # em máquinas multi-core (ex.: Raspberry Pi 4).
    MALLOC_ARENA_MAX=2 \
    WEB_CONCURRENCY=1

WORKDIR /app

# Instala dependências primeiro para aproveitar o cache de camadas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação.
COPY app ./app

# Diretório de dados persistentes (banco SQLite + mídias).
RUN mkdir -p /app/data/media

EXPOSE 8000

# Sobe o servidor com perfil enxuto: 1 worker, concorrência limitada e
# keep-alive curto. Em máquinas mais potentes, aumente --workers/--limit-concurrency.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "64", "--timeout-keep-alive", "5"]
