# Multi-stage Dockerfile for NovaAvatar

# Base stage with common dependencies
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04 AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Development stage
FROM base AS development

# Install dev dependencies
COPY requirements-dev.txt .
RUN pip3 install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p storage/generated storage/videos storage/queue logs

ENV PYTHONUNBUFFERED=1

# Test stage
FROM development AS test

# Run tests
CMD ["pytest", "tests/", "-v", "--cov"]

# Production stage
FROM base AS production

# Copy only necessary files
COPY services/ ./services/
COPY api/ ./api/
COPY frontend/ ./frontend/
COPY config/ ./config/
COPY OmniAvatar/ ./OmniAvatar/
COPY configs/ ./configs/
COPY scripts/ ./scripts/
COPY run.py .
COPY .env.example .env

# Create directories
RUN mkdir -p storage/generated storage/videos storage/queue logs pretrained_models

# Expose ports
EXPOSE 7860 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python3", "run.py", "api"]
