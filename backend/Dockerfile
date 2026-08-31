FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

COPY pyproject.toml ./
COPY alembic.ini ./
COPY app ./app

RUN pip install --upgrade pip && pip install .

FROM base AS test

COPY tests ./tests
RUN pip install ".[dev]"
CMD ["sh", "-c", "ruff check . && pytest"]

FROM base AS runtime

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
