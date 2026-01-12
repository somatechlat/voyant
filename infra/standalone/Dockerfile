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

# Install Playwright browsers (Chromium only for smaller image)
RUN playwright install chromium

# Copy application code
COPY manage.py ./manage.py
COPY voyant/ ./voyant/
COPY voyant_app/ ./voyant_app/
COPY voyant_project/ ./voyant_project/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
EXPOSE 8000
CMD ["uvicorn", "voyant_project.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
