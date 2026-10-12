"""gunicorn configuration (used automatically when started from this directory)."""

import os
import socket


def _ipv6_available():
    if not socket.has_ipv6:
        return False
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as sock:
            sock.bind(("::", 0))
    except OSError:
        return False
    return True


# Railway injects PORT; 8000 is the local default. "[::]" listens on IPv6 and
# IPv4 at the same time – Railway's proxy and private network may connect over
# IPv6, which an IPv4-only socket refuses (the proxy then answers 502).
# Hosts without IPv6 fall back to IPv4.
_host = "[::]" if _ipv6_available() else "0.0.0.0"
bind = f"{_host}:{os.environ.get('PORT', '8000')}"

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
