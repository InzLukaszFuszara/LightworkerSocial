"""behave(-django) hooks. Run with: python manage.py behave"""

import os
import shutil
import tempfile

from django.test.utils import override_settings

# Playwright's sync API runs an event loop in the main thread; Django would
# otherwise refuse ORM calls made from browser scenarios.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


def _default_chromium():
    # Pre-installed Chromium (e.g. in CI containers); otherwise let
    # Playwright use the browser downloaded by "playwright install".
    candidate = "/opt/pw-browsers/chromium"
    return candidate if os.path.exists(candidate) else None


def before_all(context):
    context.media_root = tempfile.mkdtemp(prefix="lws-media-")
    context._media_override = override_settings(
        MEDIA_ROOT=context.media_root,
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )
    context._media_override.enable()


def after_all(context):
    context._media_override.disable()
    shutil.rmtree(context.media_root, ignore_errors=True)


def before_scenario(context, scenario):
    context.users = {}
    context.categories = {}
    context.posts = {}
    context.response = None
    context.upload_files = []
    context.browser = None
    context.cleanups = []  # callables run after the scenario (e.g. stop a test SMTP server)
    if "browser" in scenario.effective_tags:
        _start_browser(context, scenario)


def after_scenario(context, scenario):
    for cleanup in reversed(context.cleanups):
        cleanup()
    # Close the browser before behave-django tears down the live server.
    if context.browser:
        context.page.close()
        context.browser.close()
        context.playwright.stop()
        context.browser = None


def _start_browser(context, scenario):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:  # pragma: no cover - optional dependency
        scenario.skip("Playwright is not installed")
        return
    context.playwright = sync_playwright().start()
    context.browser = context.playwright.chromium.launch(
        executable_path=os.environ.get("CHROMIUM_PATH") or _default_chromium()
    )
    context.page = context.browser.new_page(locale="pl-PL")
    context.console_errors = []
    context.page.on("pageerror", lambda exc: context.console_errors.append(str(exc)))
