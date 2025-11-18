# collector/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install telethon httpx python-dotenv requests

COPY . .

CMD ["python", "collector.py"]