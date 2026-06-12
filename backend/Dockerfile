# Imagem do backend AdSignage (FastAPI + Uvicorn).
FROM python:3.12-slim

# Evita arquivos .pyc e garante logs sem buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências primeiro para aproveitar o cache de camadas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação.
COPY app ./app

# Diretório de dados persistentes (banco SQLite + mídias).
RUN mkdir -p /app/data/media

EXPOSE 8000

# Sobe o servidor. Em produção, ajuste --workers conforme a máquina.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
