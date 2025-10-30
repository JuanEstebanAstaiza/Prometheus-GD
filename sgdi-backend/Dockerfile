# Multi-stage build for SGDI Backend

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r sgdi && useradd -r -g sgdi sgdi

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Ensure models/__init__.py is correctly populated
RUN python models_init_backup.py

# Create necessary directories and make start script executable
RUN mkdir -p /app/storage /app/backups /app/logs && \
    chmod +x /app/start.sh && \
    chown -R sgdi:sgdi /app

# Switch to non-root user
USER sgdi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application directly without reload (ensures CORS loads)
CMD ["sh", "-c", "python seed_admin.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-reload"]
