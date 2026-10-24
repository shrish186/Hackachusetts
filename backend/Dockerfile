# Fathom backend (FastAPI). Build from the REPO ROOT so config/ and data/ are in context:
#   docker build -f backend/Dockerfile -t fathom-backend .
#   docker run -p 8000:8000 fathom-backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FATHOM_ROOT=/srv/fathom \
    FATHOM_DEMO_MODE=true \
    PORT=8000

WORKDIR /srv/fathom

# Runtime dependencies only (test/ingest-only packages such as pytest,
# hypothesis, geopandas, xarray are not installed).
RUN pip install \
      "fastapi>=0.110" \
      "uvicorn>=0.29" \
      "pydantic>=2.6" \
      "pyyaml>=6" \
      "numpy>=1.26" \
      "shapely>=2.0" \
      "httpx>=0.27"

COPY config ./config
COPY data/snapshots ./data/snapshots
COPY backend/app ./backend/app

RUN useradd --create-home --uid 10001 fathom \
    && chown -R fathom:fathom /srv/fathom
USER fathom

WORKDIR /srv/fathom/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8000'), timeout=4)" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-server-header"]
