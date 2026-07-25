# FastAPI backend — container image for Render (or any container host).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (see .dockerignore for what's excluded: venv, __pycache__, .env, uploads).
COPY . .

# Render injects $PORT; default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

# Migrations run at startup: Render's free plan offers neither a pre-deploy
# command nor shell access. `alembic upgrade head` is idempotent, so repeated
# restarts are harmless — revisit if this ever scales past one instance.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
