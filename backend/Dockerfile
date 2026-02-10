FROM python:3.11-slim

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway sets PORT automatically
ENV HOST=0.0.0.0
ENV PORT=8001

EXPOSE ${PORT}

# Run Alembic migrations then start the server
CMD alembic upgrade head && python server.py
