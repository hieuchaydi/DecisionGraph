FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["decisiongraph", "serve", "--host", "0.0.0.0", "--port", "8000"]

