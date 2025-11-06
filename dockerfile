# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-root

COPY webhook_server ./webhook_server

ENV WEBHOOK_ENV=prod

EXPOSE 5000

CMD ["poetry", "run", "python", "-m", "webhook_server.webhook_server"]
