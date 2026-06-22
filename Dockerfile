# --- Stage 0: Frontend Builder ---
FROM node:20-slim AS frontend-builder
WORKDIR /build
# Copy package manifest first so npm install is cached independently of source changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 1: Python Dependency Builder ---
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
# Runtime deps only — test/dev deps are not needed in the final image.
COPY addon-core/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Final Production Image ---
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Compiled frontend served as static files by FastAPI.
COPY --from=frontend-builder /build/dist ./static

# Application source only — no tests in the production image.
COPY addon-core/app/ ./app/

EXPOSE 9150
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9150"]
