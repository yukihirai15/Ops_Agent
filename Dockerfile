FROM python:3.12-slim

WORKDIR /app

# System deps (for httpx, subprocess calls to docker CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
