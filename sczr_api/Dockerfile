FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    MODULE_NAME=sczr_api.main

RUN pip install --no-cache poetry==1.1.4
COPY ./poetry.lock ./pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-root --no-interaction --no-ansi
COPY sczr_api /app/sczr_api
