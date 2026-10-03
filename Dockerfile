# syntax=docker/dockerfile:1

# Stockpile production container
# - Next.js 15 standalone frontend
# - FastAPI/Python backend
# - FFmpeg for video processing
# - Single container, ports 3000 (web) and 8000 (API)

# ============================================================
# 1. Build the Next.js frontend
# ============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN npm run build


# ============================================================
# 2. Runtime image
# ============================================================
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_API_URL=http://127.0.0.1:8000 \
    PORT=8000 \
    HOST=0.0.0.0

# FFmpeg is required by the video pipeline.
# Node.js is required to run the Next.js standalone server.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better Docker layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend/application source.
COPY ai_broll_autopilot/ ./ai_broll_autopilot/
COPY src/ ./src/
COPY gbro-collage-broll/ ./gbro-collage-broll/
COPY erduo-broll-loop-engineering/ ./erduo-broll-loop-engineering/
COPY models/ ./models/
COPY autopilot.py stockpile.py ./

# Runtime directories. Mount these from the host/volume in production
# so source videos, generated media and job state survive container restarts.
RUN mkdir -p \
        /app/input \
        /app/output \
        /app/media \
        /app/data

# Copy the Next.js standalone production server.
COPY --from=frontend-builder /app/web/.next/standalone/ /app/web-standalone/
COPY --from=frontend-builder /app/web/.next/static/ /app/web-standalone/.next/static/
COPY --from=frontend-builder /app/web/public/ /app/web-standalone/public/

# Container entrypoint starts both services.
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 3000 8000

# Docker-level health check uses Stockpile's /api/health endpoint.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

ENTRYPOINT ["/bin/bash", "/app/docker-entrypoint.sh"]
