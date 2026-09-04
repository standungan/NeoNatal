# FastAPI backend — container image for Render (or any container host).
# 3.10, not 3.13: every suite in tests/ has only ever been run on 3.10 (the local
# venv is 3.10.11), every pin in requirements.txt resolves a cp310 wheel, and
# nothing in app/ uses 3.11+ syntax. Shipping 3.13 would put a runtime into the
# hospital that no test has ever executed on. Move it up deliberately, after
# running the suites on the new version - not as an unexamined default.
FROM python:3.10-slim

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
