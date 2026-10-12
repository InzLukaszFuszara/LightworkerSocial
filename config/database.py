"""Database configuration read from environment variables.

PostgreSQL (psycopg 3) is used when ``DATABASE_URL`` or the ``PGHOST`` family
of variables is set – Railway's PostgreSQL service provides both. Otherwise
the project falls back to a local SQLite file.
"""

from urllib.parse import parse_qs, unquote, urlsplit

POSTGRES_SCHEMES = {"postgres", "postgresql", "pgsql", "postgresql+psycopg"}


def _postgres(name, user, password, host, port, options, env):
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": str(port or "5432"),
        # Keep connections open between requests; checked before reuse.
        "CONN_MAX_AGE": int(env.get("DJANGO_DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": options,
    }


def database_settings(env, base_dir):
    url = env.get("DATABASE_URL", "").strip()
    if url:
        parts = urlsplit(url)
        if parts.scheme not in POSTGRES_SCHEMES:
            raise ValueError(f"Unsupported DATABASE_URL scheme: {parts.scheme!r}")
        query = {k: v[-1] for k, v in parse_qs(parts.query).items()}
        options = {}
        if "sslmode" in query:
            options["sslmode"] = query["sslmode"]
        return _postgres(
            unquote(parts.path.lstrip("/")),
            unquote(parts.username or ""),
            unquote(parts.password or ""),
            parts.hostname or "",
            parts.port,
            options,
            env,
        )
    if env.get("PGHOST"):
        return _postgres(
            env.get("PGDATABASE", ""),
            env.get("PGUSER", ""),
            env.get("PGPASSWORD", ""),
            env["PGHOST"],
            env.get("PGPORT"),
            {},
            env,
        )
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env.get("DJANGO_DB_PATH", str(base_dir / "db.sqlite3")),
    }
