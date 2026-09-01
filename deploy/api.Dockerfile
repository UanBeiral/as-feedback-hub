FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN pip install --upgrade pip && pip install -e apps/api

COPY apps/api/app apps/api/app
COPY alembic alembic
COPY alembic.ini alembic.ini

ENV PYTHONPATH=/srv/apps/api

# Roda sem privilégio: um RCE na aplicação não vira root no container.
RUN useradd --create-home --uid 10001 app && chown -R app:app /srv
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
