# backend/Dockerfile

FROM python:3.11-slim AS builder

WORKDIR /app

# Install gcc - needed to compile psycopg (PostgreSQL driver).
# Clean up apt cache in the same layer to keep image size down.
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first so Docker can cache this layer.
# pip install only re-runs when requirements.txt changes,
# not on every code change.
RUN pip install --upgrade pip wheel
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN useradd -m appuser
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY . .
USER appuser
EXPOSE 8000

# APP_ENV=docker tells database.py to load .env.docker
ENV APP_ENV=docker

CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]