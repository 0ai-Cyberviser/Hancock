# syntax=docker/dockerfile:1
# Multi-stage build for Hancock — AI-powered cybersecurity agent by CyberViser

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="Johnny Watters <0ai@cyberviserai.com>"
LABEL description="Hancock — AI-powered cybersecurity agent maintained by Johnny Watters (0ai-Cyberviser) (multi-stage)"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY hancock_agent.py .
COPY hancock_constants.py .
COPY input_validator.py .
COPY orchestration_controller.py .
COPY collectors/ collectors/
COPY formatter/ formatter/

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

RUN useradd -m hancock
USER hancock

CMD ["python", "hancock_agent.py", "--server", "--port", "5000"]
