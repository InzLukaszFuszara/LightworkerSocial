# Production image for Railway (or any Docker host).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so code changes reuse this layer.
# Pillow (with WebP) and psycopg[binary] ship as wheels – no system packages needed.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Hashed + compressed static files for WhiteNoise. The key is only used for
# this build step; the real one comes from the environment at runtime.
RUN DJANGO_DEBUG=0 DJANGO_SECRET_KEY=collectstatic-only \
    python manage.py collectstatic --noinput

# Railway volumes are mounted as root, so the app runs as root to be able to
# write uploads there.
EXPOSE 8000
CMD ["./docker-entrypoint.sh"]
