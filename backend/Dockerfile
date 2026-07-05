# Backend image for Render — includes the OCR toolchain so scanned PDFs work.
#
# System dependencies:
#   tesseract-ocr            OCR engine
#   tesseract-ocr-eng        English language pack
#   tesseract-ocr-chi-sim    Simplified Chinese language pack
#   poppler-utils            pdftoppm/pdfinfo, used by pdf2image to rasterize pages
#
# OCR remains OPTIONAL at runtime (FRA_ENABLE_OCR); the app parses digital PDFs
# directly and only falls back to OCR for image/scanned pages.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRA_ENABLE_OCR=true \
    FRA_OCR_LANGUAGES=chi_sim+eng

RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-chi-sim \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching), then the app.
COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY alembic ./alembic
RUN pip install -e '.[postgres,preprocess,ocr]'

EXPOSE 8000

# Run migrations, then serve. create_all also runs on startup as a safety net.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
