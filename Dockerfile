FROM python:3.11-slim

# Set working directory
WORKDIR /app

# ── System dependencies ────────────────────────────────────────────────────────
# Install only what's needed; clean apt cache in the same layer to keep image small.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ────────────────────────────────────────────────────────
# Copy requirements first to leverage Docker layer caching.
# The heavy pip install layer only reruns when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Entrypoint script ─────────────────────────────────────────────────────────
# Runs Alembic migrations then starts the server.
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# ── Security: non-root user ───────────────────────────────────────────────────
# Running as root inside a container is a security risk.
# Create a dedicated user with no shell and no home directory.
RUN adduser --disabled-password --gecos "" --no-create-home appuser
USER appuser

# ── Network ───────────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Health check ──────────────────────────────────────────────────────────────
# Docker uses this to determine if the container is healthy.
# If /health returns non-2xx, Docker marks the container as unhealthy
# and orchestrators (Compose, Kubernetes, Railway) will restart it.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Start command ─────────────────────────────────────────────────────────────
# gunicorn manages worker processes; each worker runs uvicorn (ASGI).
# WEB_CONCURRENCY defaults to 2 (safe for small deployments).
# Override with: docker run -e WEB_CONCURRENCY=4 ...
ENTRYPOINT ["/docker-entrypoint.sh"]
