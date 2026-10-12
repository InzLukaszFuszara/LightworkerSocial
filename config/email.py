"""E-mail (SMTP) configuration read from environment variables."""

TRUE_VALUES = {"1", "true", "yes", "on"}


def _flag(env, name, default):
    return env.get(name, default).strip().lower() in TRUE_VALUES


def email_settings(env, debug=False):
    """Return Django e-mail settings for the given environment.

    When ``EMAIL_HOST`` is set, messages are sent through SMTP. Without it,
    development (``debug``) prints e-mails to the console; production still
    uses SMTP so that a missing configuration fails loudly instead of
    silently dropping activation e-mails.
    """
    host = env.get("EMAIL_HOST", "").strip()
    use_ssl = _flag(env, "EMAIL_USE_SSL", "0")
    use_tls = _flag(env, "EMAIL_USE_TLS", "0" if use_ssl else "1")
    if use_ssl and use_tls:
        raise ValueError("EMAIL_USE_TLS and EMAIL_USE_SSL are mutually exclusive")
    if host:
        backend = "django.core.mail.backends.smtp.EmailBackend"
    elif debug:
        backend = "django.core.mail.backends.console.EmailBackend"
    else:
        backend = "django.core.mail.backends.smtp.EmailBackend"
    backend = env.get("EMAIL_BACKEND", backend)
    default_port = "465" if use_ssl else "587"
    return {
        "EMAIL_BACKEND": backend,
        "EMAIL_HOST": host or "localhost",
        "EMAIL_PORT": int(env.get("EMAIL_PORT", default_port)),
        "EMAIL_HOST_USER": env.get("EMAIL_HOST_USER", ""),
        "EMAIL_HOST_PASSWORD": env.get("EMAIL_HOST_PASSWORD", ""),
        "EMAIL_USE_TLS": use_tls,
        "EMAIL_USE_SSL": use_ssl,
        "EMAIL_TIMEOUT": int(env.get("EMAIL_TIMEOUT", "10")),
        "DEFAULT_FROM_EMAIL": env.get(
            "DEFAULT_FROM_EMAIL", "Lightworker Social <no-reply@localhost>"
        ),
    }
