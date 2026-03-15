FROM python:3.12-slim

# Keep Python runtime predictable in containers.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# Install Poetry once, then install app dependencies using lockfile for repeatable builds.
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

# Copy only runtime backend sources (no secrets/.env should ever be copied).
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Create an unprivileged runtime user and writable SQLite directory.
RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/data \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
