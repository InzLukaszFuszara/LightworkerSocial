"""Django e-mail backend that sends messages through the Mailgun HTTP API.

The complete MIME message built by Django (plain text, HTML alternative,
attachments, headers) is posted to Mailgun's ``messages.mime`` endpoint, so
e-mails look exactly the same as when they are sent over SMTP. Only the
standard library is used – no extra dependencies are needed.
"""

import base64
import logging
import urllib.error
import urllib.request
import uuid

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class MailgunError(OSError):
    """Mailgun rejected the message or could not be reached."""


def _multipart(fields, files):
    """Encode ``fields`` and ``files`` as ``multipart/form-data``."""
    boundary = uuid.uuid4().hex
    lines = []
    for name, value in fields:
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            value.encode("utf-8"),
        ]
    for name, filename, content in files:
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode(),
            b"Content-Type: message/rfc822",
            b"",
            content,
        ]
    lines += [f"--{boundary}--".encode(), b""]
    return b"\r\n".join(lines), f"multipart/form-data; boundary={boundary}"


class EmailBackend(BaseEmailBackend):
    def __init__(self, api_key=None, domain=None, api_url=None, timeout=None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.MAILGUN_API_KEY
        self.domain = domain or settings.MAILGUN_DOMAIN
        self.api_url = (api_url or settings.MAILGUN_API_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.EMAIL_TIMEOUT
        if not self.fail_silently and not (self.api_key and self.domain):
            raise ImproperlyConfigured("MAILGUN_API_KEY and MAILGUN_DOMAIN must be set")

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                if self._send(message):
                    sent += 1
            except (MailgunError, OSError):
                if not self.fail_silently:
                    raise
                logger.exception("Mailgun could not send the e-mail")
        return sent

    def _send(self, message):
        recipients = message.recipients()
        if not recipients:
            return False
        fields = [("to", address) for address in recipients]
        files = [("message", "message.mime", message.message().as_bytes(linesep="\r\n"))]
        body, content_type = _multipart(fields, files)
        credentials = base64.b64encode(f"api:{self.api_key}".encode()).decode()
        request = urllib.request.Request(
            f"{self.api_url}/v3/{self.domain}/messages.mime",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": content_type,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:500]
            raise MailgunError(f"Mailgun returned HTTP {error.code}: {detail}") from error
        return True
