FROM python:3.11-slim

WORKDIR /app

# Copia il codice
COPY ./app /app

# Aggiorna pip e installa librerie
RUN pip install --upgrade pip
RUN pip install fastapi uvicorn[standard] SQLAlchemy[asyncio] asyncpg celery[redis] requests beautifulsoup4 python-dotenv httpx

# Espone la porta FastAPI
EXPOSE 8000

# Comando di avvio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
