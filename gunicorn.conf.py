"""gunicorn configuration (used automatically when started from this directory)."""

import os

# Railway injects PORT; 8000 is the local default.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Threads suit this app: the messenger polls with many short requests.
worker_class = "gthread"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 20
keepalive = 5

# Recycle workers now and then to keep memory in check.
max_requests = 1000
max_requests_jitter = 100

# Railway terminates TLS in its proxy.
forwarded_allow_ips = "*"

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
