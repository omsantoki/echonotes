# EchoNotes API — production image (CPU-only, PROVIDER=openai).
FROM python:3.11-slim

# ffmpeg is required by the OpenAI transcription path: app/transcribe.py shells
# out to it to chunk audio larger than 24 MB (real lectures hit this).
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Render injects $PORT — bind 0.0.0.0. Multiple workers are safe because all
# state is external (Postgres + Qdrant + object storage), not local files.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
