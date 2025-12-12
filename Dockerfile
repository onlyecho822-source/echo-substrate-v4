FROM python:3.11-slim

# Security: Run as non-root user
RUN useradd -m -u 1000 substrate && \
    mkdir -p /app && \
    chown -R substrate:substrate /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-client \
        && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY --chown=substrate:substrate pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY --chown=substrate:substrate src/ ./src/
COPY --chown=substrate:substrate config/ ./config/

# Switch to non-root user
USER substrate

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
