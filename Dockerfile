# ============================================================
# ATS Resume Analyzer v2 — Production Dockerfile
# ============================================================
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    FRONTEND_DIR=/app/frontend \
    DEBIAN_FRONTEND=noninteractive

# System deps: OCR + PDF + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY ats-v2/backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir sentence-transformers

# Copy backend source
COPY ats-v2/backend/ ./

# Copy frontend (served as static files via FastAPI)
COPY ats-v2/frontend/ ./frontend/

# Create data directory for SQLite DB (can be volume-mounted)
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

CMD ["sh", "-c", "uvicorn main:app --host ${HOST} --port ${PORT} --workers 2 --log-level info"]
