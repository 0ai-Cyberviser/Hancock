# ─── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="CyberViser <contact@cyberviser.ai>"
LABEL description="Hancock — AI-powered cybersecurity agent by CyberViser"
LABEL org.opencontainers.image.source="https://github.com/0ai-Cyberviser/Hancock"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY hancock_agent.py hancock_pipeline.py hancock_constants.py ./
COPY collectors/ collectors/
COPY formatter/ formatter/
COPY monitoring/ monitoring/

# Create non-root user
RUN useradd -r -u 1000 -g 0 -s /sbin/nologin hancock \
    && mkdir -p /app/data \
    && chown -R hancock:0 /app \
    && chmod -R g=u /app

USER 1000

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" \
    || exit 1

CMD ["python", "hancock_agent.py", "--server", "--port", "5000"]
