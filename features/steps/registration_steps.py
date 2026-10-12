"""Step definitions for e-mail confirmation of new accounts."""

import base64
import re
import socket
import threading
import time
from email import message_from_bytes, policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from behave import given, then, when
from django.contrib.auth import get_user_model
from django.core import mail
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from helpers import soup

from config.email import MAILGUN_BACKEND, email_settings

User = get_user_model()
ACTIVATION_LINK = re.compile(r"https?://[^\s\"'<>]+/accounts/activate/[^\s\"'<>/]+/")
PASSWORD = "S3cret-pass!"


def _client(context):
    return context.test.client


def _emails_to(address):
    return [m for m in mail.outbox if address in m.to]


def _last_email_to(address):
    emails = _emails_to(address)
    assert emails, f"No e-mail was sent to {address}"
    return emails[-1]


def _activation_link(address):
    links = ACTIVATION_LINK.findall(_last_email_to(address).body)
    assert links, "No activation link in the e-mail"
    return links[0]


def _signup(context, email, username):
    context.response = _client(context).post(
        reverse("accounts:signup"),
        {"email": email, "username": username, "password1": PASSWORD, "password2": PASSWORD},
    )
    assert context.response.status_code == 302, context.response.content


def _open(context, url):
    context.response = _client(context).get(url)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _use_settings(context, **settings):
    override = override_settings(**settings)
    override.enable()
    context.cleanups.append(override.disable)


# --------------------------------------------------------------------------
# Signing up & activation
# --------------------------------------------------------------------------


@given('I signed up with e-mail "{email:Q}" and username "{username:Q}"')
def step_signed_up(context, email, username):
    _signup(context, email, username)


@given('I signed up with e-mail "{email:Q}" and username "{username:Q}" {minutes:d} minutes ago')
def step_signed_up_ago(context, email, username, minutes):
    _signup(context, email, username)
    User.objects.filter(email=email).update(
        activation_sent_at=timezone.now() - timezone.timedelta(minutes=minutes)
    )


@given('I opened the activation link from the e-mail to "{email:Q}"')
@when('I open the activation link from the e-mail to "{email:Q}"')
def step_open_link(context, email):
    _open(context, _activation_link(email))


@when('I open the activation link from the e-mail to "{email:Q}" {days:d} days later')
def step_open_link_later(context, email, days):
    link = _activation_link(email)
    later = time.time() + days * 24 * 60 * 60
    with mock.patch("django.core.signing.time.time", return_value=later):
        _open(context, link)


@when('I open a tampered activation link from the e-mail to "{email:Q}"')
def step_open_tampered(context, email):
    link = _activation_link(email)
    token = link.rstrip("/").rsplit("/", 1)[1]
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    _open(context, link.replace(token, tampered))


@when('I request a new activation link for "{email:Q}"')
def step_resend(context, email):
    context.response = _client(context).post(
        reverse("accounts:resend_activation"), {"email": email}, follow=True
    )


@then('I should be redirected to the page "{heading:Q}"')
def step_redirected_to_page(context, heading):
    assert context.response.status_code == 302, context.response.status_code
    context.response = _client(context).get(context.response["Location"])
    title = soup(context.response).select_one("h1").get_text(strip=True)
    assert title == heading, title


@then('the account "{email:Q}" should be waiting for activation')
def step_waiting(context, email):
    user = User.objects.get(email=email)
    assert not user.is_active and not user.email_verified, (user.is_active, user.email_verified)


@then('the account "{email:Q}" should be active')
def step_active(context, email):
    user = User.objects.get(email=email)
    assert user.is_active and user.email_verified


@then("the page should contain a link to resend the activation e-mail")
def step_resend_link(context):
    href = reverse("accounts:resend_activation")
    assert soup(context.response).select(f'a[href^="{href}"]'), "No resend link"


# --------------------------------------------------------------------------
# E-mails
# --------------------------------------------------------------------------


@then('{count:d} e-mail should have been sent to "{email:Q}"')
@then('{count:d} e-mails should have been sent to "{email:Q}"')
def step_email_count(context, count, email):
    actual = len(_emails_to(email))
    assert actual == count, f"{actual} e-mails"


@then("no e-mail should have been sent")
def step_no_email(context):
    assert not mail.outbox, [m.subject for m in mail.outbox]


@then('the e-mail should have the subject "{subject:Q}"')
def step_subject(context, subject):
    assert mail.outbox, "No e-mail was sent"
    assert mail.outbox[-1].subject == subject, mail.outbox[-1].subject


@then("the e-mail should contain an activation link")
def step_contains_link(context):
    assert ACTIVATION_LINK.search(mail.outbox[-1].body), mail.outbox[-1].body


@then("the e-mail should have an HTML version with the activation link")
def step_html_version(context):
    message = mail.outbox[-1]
    html = [content for content, mimetype in message.alternatives if mimetype == "text/html"]
    assert html, "No HTML alternative"
    assert ACTIVATION_LINK.search(html[0]), html[0]


# --------------------------------------------------------------------------
# SMTP
# --------------------------------------------------------------------------


@given("the SMTP server is unreachable")
def step_smtp_unreachable(context):
    _use_settings(
        context,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="127.0.0.1",
        EMAIL_PORT=_free_port(),  # nothing listens there
        EMAIL_USE_TLS=False,
        EMAIL_USE_SSL=False,
        EMAIL_TIMEOUT=2,
    )


class _RecordingHandler:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope)
        return "250 OK"


@given("a test SMTP server is running")
def step_smtp_server(context):
    try:
        from aiosmtpd.controller import Controller
    except ImportError:  # pragma: no cover - optional dependency
        context.scenario.skip("aiosmtpd is not installed")
        return
    handler = _RecordingHandler()
    port = _free_port()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()
    context.cleanups.append(controller.stop)
    context.smtp_handler = handler
    _use_settings(
        context,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="127.0.0.1",
        EMAIL_PORT=port,
        EMAIL_USE_TLS=False,
        EMAIL_USE_SSL=False,
        EMAIL_TIMEOUT=5,
    )


@then('the SMTP server should have received an e-mail for "{email:Q}"')
def step_smtp_received(context, email):
    received = [m for m in context.smtp_handler.messages if email in m.rcpt_tos]
    assert received, [m.rcpt_tos for m in context.smtp_handler.messages]
    context.smtp_message = received[-1]


@then("the received e-mail should contain an activation link")
def step_smtp_link(context):
    # The text part may be quoted-printable/base64 encoded; check the parsed message.
    message = message_from_bytes(context.smtp_message.content, policy=policy.default)
    text = message.get_body(preferencelist=("plain",)).get_content()
    assert ACTIVATION_LINK.search(text), text


@given('the environment variables "{variables:Q}"')
def step_env(context, variables):
    env = dict(pair.split("=", 1) for pair in variables.split(";") if pair)
    debug = env.pop("DEBUG", "0") == "1"
    context.email_config = email_settings(env, debug=debug)


@then('the e-mail backend should be "{name:Q}"')
def step_backend(context, name):
    backend = context.email_config["EMAIL_BACKEND"]
    expected = MAILGUN_BACKEND if name == "mailgun" else f"django.core.mail.backends.{name}.EmailBackend"
    assert backend == expected, backend


@then('the e-mail setting "{setting:Q}" should be "{value:Q}"')
def step_email_setting(context, setting, value):
    actual = str(context.email_config[setting])
    assert actual == value, actual


# --------------------------------------------------------------------------
# Mailgun
# --------------------------------------------------------------------------


class _FakeMailgunHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.received.append((self.path, dict(self.headers), body))
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"id": "<test@mailgun>", "message": "Queued. Thank you."}')

    def log_message(self, *args):
        pass


def _start_fake_mailgun(context, status):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeMailgunHandler)
    server.received = []
    server.status = status
    threading.Thread(target=server.serve_forever, daemon=True).start()
    context.cleanups.append(server.server_close)
    context.cleanups.append(server.shutdown)
    context.mailgun = server
    _use_settings(
        context,
        EMAIL_BACKEND=MAILGUN_BACKEND,
        MAILGUN_API_KEY="key-test",
        MAILGUN_DOMAIN="mg.example.com",
        MAILGUN_API_URL=f"http://127.0.0.1:{server.server_address[1]}",
        EMAIL_TIMEOUT=5,
    )


@given("a test Mailgun API is running")
def step_mailgun_server(context):
    _start_fake_mailgun(context, 200)


@given("the Mailgun API rejects messages")
def step_mailgun_rejects(context):
    _start_fake_mailgun(context, 401)


@then('the Mailgun API should have received an e-mail for "{email:Q}"')
def step_mailgun_received(context, email):
    received = context.mailgun.received
    assert len(received) == 1, received
    path, headers, body = received[0]
    assert path == "/v3/mg.example.com/messages.mime", path
    expected = "Basic " + base64.b64encode(b"api:key-test").decode()
    assert headers.get("Authorization") == expected
    content_type = headers["Content-Type"]
    form = message_from_bytes(
        f"Content-Type: {content_type}\r\n\r\n".encode() + body, policy=policy.default
    )
    parts = {part.get_param("name", header="content-disposition"): part for part in form.iter_parts()}
    assert parts["to"].get_payload(decode=True).decode() == email
    mime = parts["message"].get_payload(decode=True) or parts["message"].get_payload()[0].as_bytes()
    context.mailgun_message = message_from_bytes(mime, policy=policy.default)


@then("the Mailgun e-mail should contain an activation link")
def step_mailgun_link(context):
    message = context.mailgun_message
    text = message.get_body(preferencelist=("plain",)).get_content()
    assert ACTIVATION_LINK.search(text), text
    assert message.get_body(preferencelist=("html",)) is not None
