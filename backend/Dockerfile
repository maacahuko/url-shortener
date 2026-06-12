# ── Build stage ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies into a separate layer for caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app.py .

# Don't run as root
RUN useradd --no-create-home appuser
USER appuser

EXPOSE 5000

# Gunicorn: 2 workers, bind to all interfaces on port 5000
# init_db() is called inside app.py on startup via gunicorn's --preload flag
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "--preload", "--access-logfile", "-", "app:app"]
