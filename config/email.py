"""E-mail (SMTP or Mailgun) configuration read from environment variables."""

TRUE_VALUES = {"1", "true", "yes", "on"}
MAILGUN_BACKEND = "config.mailgun.EmailBackend"
MAILGUN_API_URLS = {
    "us": "https://api.mailgun.net",
    "eu": "https://api.eu.mailgun.net",
}


def _flag(env, name, default):
    return env.get(name, default).strip().lower() in TRUE_VALUES


def email_settings(env, debug=False):
    """Return Django e-mail settings for the given environment.

    When ``MAILGUN_API_KEY`` and ``MAILGUN_DOMAIN`` are set, messages are sent
    through the Mailgun HTTP API. Otherwise, when ``EMAIL_HOST`` is set,
    messages are sent through SMTP. Without either,
    development (``debug``) prints e-mails to the console; production still
    uses SMTP so that a missing configuration fails loudly instead of
    silently dropping activation e-mails.
    """
    host = env.get("EMAIL_HOST", "").strip()
    use_ssl = _flag(env, "EMAIL_USE_SSL", "0")
    use_tls = _flag(env, "EMAIL_USE_TLS", "0" if use_ssl else "1")
    if use_ssl and use_tls:
        raise ValueError("EMAIL_USE_TLS and EMAIL_USE_SSL are mutually exclusive")
    mailgun_key = env.get("MAILGUN_API_KEY", "").strip()
    mailgun_domain = env.get("MAILGUN_DOMAIN", "").strip()
    region = env.get("MAILGUN_REGION", "us").strip().lower() or "us"
    if region not in MAILGUN_API_URLS:
        raise ValueError("MAILGUN_REGION must be 'us' or 'eu'")
    if mailgun_key and mailgun_domain:
        backend = MAILGUN_BACKEND
    elif host:
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
        "MAILGUN_API_KEY": mailgun_key,
        "MAILGUN_DOMAIN": mailgun_domain,
        "MAILGUN_API_URL": env.get("MAILGUN_API_URL", MAILGUN_API_URLS[region]).strip(),
        "DEFAULT_FROM_EMAIL": env.get(
            "DEFAULT_FROM_EMAIL", "Lightworker Social <no-reply@localhost>"
        ),
    }
