# Stage 1: Build frontend
FROM node:20-slim AS frontend
WORKDIR /app/web
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci
COPY apps/web/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY growgrid_core/ growgrid_core/
COPY apps/api/ apps/api/
COPY data/ data/

# Copy built frontend
COPY --from=frontend /app/web/dist apps/web/dist/

# Initialize database from CSVs
RUN python -c "from growgrid_core.db.db_loader import load_all; c = load_all(); c.close()"

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run FastAPI
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
