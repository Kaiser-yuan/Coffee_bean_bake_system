FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .

COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

RUN mkdir -p data/uploads

EXPOSE 8000

# Production entrypoint — migrate then serve. If migration fails the container
# must exit (set -e). Uvicorn takes over only after a successful upgrade.
CMD ["sh", "-c", "set -e && alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
