FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir hatchling && pip install --no-cache-dir -e .

COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/
COPY data/ data/

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && gunicorn app.main:app -w ${UVICORN_WORKERS:-5} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --graceful-timeout 30"]
