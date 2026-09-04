# ==============================================================================
# Sovereign Multimodal Local RAG Container
# Completely air-gapped, on-premises production container
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOVEREIGN_MODE=true \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1 \
    PORT=8000

# Install minimal OS dependencies for PDF rendering and OCR (OpenCV, MuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and benchmarks
COPY src/ ./src/
COPY evaluation/ ./evaluation/
COPY demo/ ./demo/
COPY .env.example ./.env

# Create data directories and non-root user
RUN mkdir -p /app/data/documents /app/data/qdrant /app/logs && \
    useradd -m sovereign && \
    chown -R sovereign:sovereign /app

USER sovereign

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
