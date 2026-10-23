# ------------------------------------------------------------------------------
# StockSense AI - Production Container
# Multi-stage build: Frontend (Node.js) + Backend (Python Flask)
# ------------------------------------------------------------------------------

# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Runtime
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Install dependencies
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source and sample data
COPY backend/ backend/
COPY sample_data/ sample_data/

# Copy compiled frontend SPA dist
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Pre-seed initial database & models
RUN python -c "from backend.database import init_db; from backend.services.sample_data_service import seed_demonstration_data; init_db(); seed_demonstration_data()"

EXPOSE 5000

# Start production WSGI server with dynamic PORT fallback
CMD exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --threads 4 "backend.app:create_app()"

