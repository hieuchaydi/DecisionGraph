FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DECISIONGRAPH_DATA_PATH=/app/data/decisiongraph.json

RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

USER appuser

EXPOSE 8000

CMD ["decisiongraph", "serve", "--host", "0.0.0.0", "--port", "8000"]
