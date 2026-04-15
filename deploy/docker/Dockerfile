# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies into a prefix directory
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="CyberViser <contact@cyberviser.ai>"
LABEL description="Hancock — AI-powered cybersecurity agent by CyberViser"
LABEL org.opencontainers.image.source="https://github.com/0ai-Cyberviser/Hancock"
LABEL org.opencontainers.image.version="0.6.0"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (ordered by change frequency — stable layers first)
COPY hancock_constants.py .
COPY hancock_agent.py .
COPY input_validator.py .
COPY orchestration_controller.py .
COPY collectors/ collectors/
COPY formatter/ formatter/
COPY monitoring/ monitoring/
COPY deploy/ deploy/

# Create non-root user
RUN useradd --no-create-home --shell /bin/false hancock \
    && mkdir -p /var/log \
    && chown hancock:hancock /var/log

# Expose API and metrics port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=5)" \
    || exit 1

# Use tini for proper signal handling if available, else Python directly
USER hancock

# Support graceful shutdown via SIGTERM
STOPSIGNAL SIGTERM

CMD ["python", "hancock_agent.py", "--server", "--port", "5000"]
