"""E-mail address confirmation: signed activation links sent over SMTP."""

import logging
import smtplib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

SALT = "accounts.activation"


class ActivationError(Exception):
    """The activation link is invalid or expired."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason  # "invalid" or "expired"


def make_token(user):
    # The e-mail is part of the payload, so a link stops working if the
    # address of the account changes.
    return signing.dumps({"u": user.pk, "e": user.email}, salt=SALT, compress=True)


def user_from_token(token):
    max_age = settings.ACCOUNT_ACTIVATION_DAYS * 24 * 60 * 60
    try:
        data = signing.loads(token, salt=SALT, max_age=max_age)
    except signing.SignatureExpired:
        raise ActivationError("expired")
    except signing.BadSignature:
        raise ActivationError("invalid")
    user = get_user_model().objects.filter(pk=data.get("u"), email=data.get("e")).first()
    if user is None:
        raise ActivationError("invalid")
    return user


def activate(user):
    user.is_active = True
    user.email_verified = True
    user.save(update_fields=["is_active", "email_verified"])


def can_resend(user):
    if user.activation_sent_at is None:
        return True
    elapsed = (timezone.now() - user.activation_sent_at).total_seconds()
    return elapsed >= settings.ACCOUNT_ACTIVATION_RESEND_SECONDS


def send_activation_email(request, user):
    """Send the activation link. Returns ``False`` if the SMTP server failed."""
    url = request.build_absolute_uri(
        reverse("accounts:activate", kwargs={"token": make_token(user)})
    )
    context = {
        "user": user,
        "activation_url": url,
        "days": settings.ACCOUNT_ACTIVATION_DAYS,
        "site_name": "Lightworker Social",
    }
    subject = render_to_string("accounts/email/activation_subject.txt", context).strip()
    body = render_to_string("accounts/email/activation_body.txt", context)
    html = render_to_string("accounts/email/activation_body.html", context)
    message = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    message.attach_alternative(html, "text/html")
    try:
        message.send()
    except (smtplib.SMTPException, OSError):
        logger.exception("Could not send the activation e-mail to %s", user.email)
        return False
    user.activation_sent_at = timezone.now()
    user.save(update_fields=["activation_sent_at"])
    return True
