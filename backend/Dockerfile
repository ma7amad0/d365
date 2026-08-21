FROM python:3.12.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system portal && useradd --system --gid portal --home /app portal
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY config ./config
COPY alembic.ini ./
COPY alembic ./alembic
RUN chown -R portal:portal /app
USER portal
EXPOSE 8000

FROM base AS test
USER root
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
RUN chown -R portal:portal /app/tests
USER portal
CMD ["pytest"]

FROM base AS production
CMD ["sh", "-c", "alembic upgrade head && exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:8000 --access-logfile - --error-logfile -"]
