# VOYANT v3.0.0 - Dockerfile
# Production image for Voyant API

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Core + DataScraper (OCR, PDF, Media, Browser)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # OCR - Tesseract with Spanish
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    # PDF processing
    poppler-utils \
    # Media processing
    ffmpeg \
    # Java for Apache Tika
    default-jre-headless \
    # Chromium dependencies for Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: transcription dependencies (CPU/GPU controlled explicitly)
# CPU-only default: VOYANT_WITH_TRANSCRIBE=0 means no Whisper/torch installed.
ARG VOYANT_WITH_TRANSCRIBE=0
ARG VOYANT_TORCH_DEVICE=cpu
ARG PYTORCH_INDEX_URL_CPU=
ARG PYTORCH_INDEX_URL_CUDA=
RUN if [ "${VOYANT_WITH_TRANSCRIBE}" = "1" ]; then \
      if [ "${VOYANT_TORCH_DEVICE}" = "cpu" ]; then \
        test -n "${PYTORCH_INDEX_URL_CPU}" || (echo "PYTORCH_INDEX_URL_CPU is required when VOYANT_TORCH_DEVICE=cpu" && exit 1); \
        pip install --no-cache-dir --index-url "${PYTORCH_INDEX_URL_CPU}" torch; \
      elif [ "${VOYANT_TORCH_DEVICE}" = "cuda" ]; then \
        test -n "${PYTORCH_INDEX_URL_CUDA}" || (echo "PYTORCH_INDEX_URL_CUDA is required when VOYANT_TORCH_DEVICE=cuda" && exit 1); \
        pip install --no-cache-dir --index-url "${PYTORCH_INDEX_URL_CUDA}" torch; \
      else \
        echo "Invalid VOYANT_TORCH_DEVICE=${VOYANT_TORCH_DEVICE} (expected cpu|cuda)" && exit 1; \
      fi; \
      pip install --no-cache-dir openai-whisper; \
    fi

# Install Playwright browsers (Chromium only for smaller image)
RUN playwright install chromium

# Copy application code
COPY manage.py ./manage.py
COPY apps/ ./apps/
COPY voyant_project/ ./voyant_project/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the application
EXPOSE 8000
CMD ["uvicorn", "voyant_project.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
