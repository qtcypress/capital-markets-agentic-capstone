# One image, several free hosts: Hugging Face Spaces, Google Cloud Run, Koyeb,
# Fly.io, Oracle Cloud, or plain `docker run` on a laptop.
#
#   docker build -t qtcap .
#   docker run -p 7860:7860 qtcap
#
# The container holds NO API keys. Students supply their own from the browser
# on each request, so there is nothing in this image worth stealing.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    QTCAP_LLM_PROVIDER=stub \
    QTCAP_PUBLIC_MODE=1 \
    QTCAP_MARKET_MODE=auto \
    PORT=7860

WORKDIR /app

# Dependencies first so a code change does not re-install them.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY tests/ ./tests/
COPY knowledge_base/ ./knowledge_base/
COPY tools/ ./tools/
COPY docs/ ./docs/
COPY pytest.ini README.md healthcheck.py ./

# Hugging Face Spaces runs the container as UID 1000 and only that user's
# directories are writable, so the snapshot and findings paths must belong to it.
RUN useradd -m -u 1000 appuser \
 && mkdir -p /app/data/snapshots /app/reports \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

HEALTHCHECK --interval=60s --timeout=6s --start-period=25s --retries=3 \
  CMD ["python", "/app/healthcheck.py"]

# Single worker: the MCP servers and the retrieval index are per-process, and a
# free tier has neither the RAM nor the CPU for more.
CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
