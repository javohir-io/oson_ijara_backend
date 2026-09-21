FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /app/uploads/avatars /app/uploads/properties

EXPOSE 8000

# Shell form (not exec/JSON form) so $PORT actually gets substituted.
# Render (and similar PaaS) inject a PORT env var the app must bind to;
# locally (docker-compose) PORT is unset, so it falls back to 8000.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
