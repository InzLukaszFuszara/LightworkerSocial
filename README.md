# Lightworker Social

A social media application built with **Python / Django** (backend + server-rendered frontend),
with **BDD** tests (behave + behave-django) and **Polish** and **English** language versions.

## Features

- **Accounts** – sign-up and login with **e-mail and password** (`accounts.User`, `USERNAME_FIELD = "email"`).
  The username is only used as the public address of the profile (`/u/<username>/`).
- **E-mail confirmation (SMTP)** – a new account stays inactive until the user opens the activation
  link sent by e-mail (plain text + HTML, in the visitor's language). The link is signed, valid for
  `ACCOUNT_ACTIVATION_DAYS` (3 days by default) and works only once; a new link can be requested
  (at most once a minute). Logging in before activation explains what to do.
- **User profile with a wall** – a profile header (name, "about me", number of posts) and a wall of posts
  shown as **tiles, 3 per row** (2 / 1 on narrower screens). Each tile contains:
  - the first **250 characters** of the post (plain text without Markdown markup),
  - a **thumbnail of the first image** of the post (WebP 480×480),
  - a **link to the post's category** (forum topic),
  - when clicked, it opens a **lightbox** with the full content and all images
    (without JavaScript the link leads to the post page).
- **Adding posts** (`/posts/new/`):
  - max. **2000 characters** (validated in the form and the model, live character counter),
  - **multiple images**, each max. **5 MiB**, formats **JPG, PNG, GIF, WebP** – all of them are
    **converted to WebP** (animated GIFs stay animated),
  - a required **category** defined by an administrator in the `/admin/` panel,
  - **Markdown** support (safely sanitised with *bleach*),
  - **#hashtag** support (including Polish characters, e.g. `#spokój`).
- **Forum** (`/forum/`) – categories shown as topics (with the number of posts and the date of the last post);
  clicking a topic shows tiles with posts from the walls of all users.
- **Hashtags** (`/tags/<hashtag>/`) – all posts of all users with the given hashtag,
  sorted newest first.
- **Languages** – Polish (default) and English; a PL/EN switcher in the header. The language is also
  chosen automatically from the browser settings. Category names and descriptions are shared by all languages.
- **Messenger** – a floating side panel on the right of the window (for logged in users):
  - currently online users grouped by status (**Available**, **Be right back**); the status is set
    in the panel and kept fresh by heartbeats, users disappear after logging out or going idle,
  - **search by nick** – filters the online lists and finds all users to start a conversation,
  - conversations open as **chat bubbles docked at the bottom** of the page (minimise / close,
    unread badges, open bubbles are remembered between pages),
  - messages of max. **250 characters**, plain text (**no Markdown**), with optional **images**
    (JPG, PNG, GIF, WebP, max. **5 MiB**, converted to **WebP**, visible only to members),
  - **group conversations**: the creator (owner) creates **rooms** shown as **tabs at the top** of the
    group bubble, every group has its **own link** (`/chat/g/<token>/`) where users ask to join,
    the owner **approves or rejects requests**, **adds members by nick**, **removes** members and
    **mutes** them temporarily – a muted member sees a **countdown** until they can write again,
  - implemented with a JSON API (`/chat/api/…`) and polling, so no extra services are needed.
- **Colour scheme** in light blue and light green.

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py createsuperuser        # log in with your e-mail
python manage.py seed_demo              # (optional) demo data, password: demo-pass-123
python manage.py runserver
```

Then add categories in the admin panel at `http://127.0.0.1:8000/admin/` (Posts → Categories).

Environment variables for production: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_DB_PATH`, `DJANGO_MEDIA_ROOT`.

### E-mail (SMTP)

Activation e-mails are sent over SMTP, configured with environment variables
(see `config/email.py`). Without `EMAIL_HOST`, the development server (`DJANGO_DEBUG=1`)
prints e-mails to the console, so you can copy the activation link from the terminal.

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_HOST` | – | SMTP server, e.g. `smtp.gmail.com` |
| `EMAIL_PORT` | `587` (`465` with SSL) | SMTP port |
| `EMAIL_HOST_USER` | – | SMTP login |
| `EMAIL_HOST_PASSWORD` | – | SMTP password / app password |
| `EMAIL_USE_TLS` | `1` | STARTTLS (port 587) |
| `EMAIL_USE_SSL` | `0` | implicit TLS (port 465); cannot be combined with `EMAIL_USE_TLS` |
| `EMAIL_TIMEOUT` | `10` | connection timeout in seconds |
| `DEFAULT_FROM_EMAIL` | `Lightworker Social <no-reply@localhost>` | sender address |
| `ACCOUNT_ACTIVATION_DAYS` | `3` | how long an activation link is valid |

```bash
export EMAIL_HOST=smtp.example.com EMAIL_HOST_USER=bot@example.com EMAIL_HOST_PASSWORD=secret
export DEFAULT_FROM_EMAIL="Lightworker Social <bot@example.com>"
python manage.py runserver
```

### E-mail (Mailgun)

E-mails can also be sent through the [Mailgun](https://www.mailgun.com/) HTTP API instead of SMTP
(`config/mailgun.py`, no extra dependencies). When both `MAILGUN_API_KEY` and `MAILGUN_DOMAIN` are
set, Mailgun is used and the SMTP settings are ignored. `DEFAULT_FROM_EMAIL` should use an address
from the Mailgun sending domain.

| Variable | Default | Description |
|----------|---------|-------------|
| `MAILGUN_API_KEY` | – | Mailgun private API key (sending key) |
| `MAILGUN_DOMAIN` | – | Mailgun sending domain, e.g. `mg.example.com` |
| `MAILGUN_REGION` | `us` | `us` or `eu` – the region your domain was created in |
| `MAILGUN_API_URL` | depends on the region | override the API base URL (e.g. for a proxy) |

```bash
export MAILGUN_API_KEY=key-... MAILGUN_DOMAIN=mg.example.com MAILGUN_REGION=eu
export DEFAULT_FROM_EMAIL="Lightworker Social <no-reply@mg.example.com>"
python manage.py runserver
```

Accounts created with `createsuperuser` or in the admin panel are active immediately.

## Deployment on Railway

The repository contains everything Railway needs: a `Dockerfile` (Railway always builds with it
when it is present), `gunicorn.conf.py`, WhiteNoise for static files and psycopg 3 for PostgreSQL.

1. **New project** → *Deploy from GitHub repo* → choose this repository.
2. **Add PostgreSQL** (*+ New → Database → PostgreSQL*).
3. In the web service → **Variables**, add:

   | Variable | Value |
   |----------|-------|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference to the database service) |
   | `DJANGO_SECRET_KEY` | a long random string, e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | SMTP for activation e-mails (see above) – or `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` (and `MAILGUN_REGION=eu`) for Mailgun |

4. **Add a volume** to the web service (*right click → Attach volume*), mount path `/data`.
   Uploaded images are stored in `$RAILWAY_VOLUME_MOUNT_PATH/media`; without a volume they are lost
   on every deploy.
5. **Settings → Networking → Generate domain.** `RAILWAY_PUBLIC_DOMAIN` is added to `ALLOWED_HOSTS`
   and `CSRF_TRUSTED_ORIGINS` automatically; for a custom domain also set `DJANGO_ALLOWED_HOSTS` and
   `DJANGO_CSRF_TRUSTED_ORIGINS` (e.g. `https://example.com`).
6. **Settings → Deploy → Healthcheck path:** `/healthz/` (checks the app and the database).
7. Create an administrator once: `railway ssh` (or *Shell* in the dashboard) →
   `python manage.py createsuperuser`, then add categories in `/admin/`.

What happens on deploy:

- **Build:** `pip install -r requirements.txt` and `collectstatic` (hashed, compressed files
  served by WhiteNoise with long-lived caching).
- **Start** (`docker-entrypoint.sh`): `python manage.py migrate`, then gunicorn on `$PORT`
  (`gthread` workers – the messenger polls with many short requests).
  To run migrations as Railway's *pre-deploy command* instead, set it to
  `python manage.py migrate --noinput` and add `RUN_MIGRATIONS=0`.
- **Production mode** is switched on automatically on Railway (`RAILWAY_ENVIRONMENT_NAME` is set):
  `DEBUG` off, HTTPS redirect behind Railway's proxy (except `/healthz/`), secure cookies,
  errors logged to the deploy logs.

Optional variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_CONCURRENCY` / `GUNICORN_THREADS` | `2` / `4` | gunicorn workers and threads per worker |
| `DJANGO_SECURE_HSTS_SECONDS` | `0` | enable HSTS once HTTPS works on all domains (e.g. `31536000`) |
| `DJANGO_SERVE_MEDIA` | `1` | Django serves uploaded post images; set `0` if a CDN/S3 serves `/media/` |
| `DJANGO_DB_CONN_MAX_AGE` | `60` | seconds a database connection is reused |
| `DJANGO_LOG_LEVEL` | `INFO` | log level |

Uploaded chat images are never public: they are only served to members of the conversation.

**Troubleshooting a 502 ("Application failed to respond")** when the deploy log shows
`Listening at: http://[::]:8080`:

- Settings → Networking → the public domain must point to the port from the log (the `PORT`
  Railway sets, usually `8080`). Click the domain, change the port, and save.
- No `GET …` lines in the deploy log means requests do not reach gunicorn – it is the port.
  Lines with status 400 mean the host is not allowed: add it to `DJANGO_ALLOWED_HOSTS`.

Run the production image locally:

```bash
docker build -t lightworker .
docker run -p 8000:8000 -e DJANGO_DEBUG=0 -e DJANGO_SECRET_KEY=change-me \
  -e DJANGO_SECURE_SSL_REDIRECT=0 -e DATABASE_URL=postgresql://user:pass@host:5432/db lightworker
```

## BDD tests

Gherkin scenarios live in the `features/` directory and step definitions in `features/steps/`.

```bash
python manage.py behave                 # all scenarios
python manage.py behave --tags=-browser # without the browser test
```

The `@smtp` scenario delivers the activation e-mail through a local test SMTP server (`aiosmtpd`).
Scenarios tagged `@browser` (`lightbox.feature`, `chat_browser.feature`) run in a real browser
(Playwright + Chromium: `playwright install chromium` or the `CHROMIUM_PATH` variable).

| File | Scope |
|------|-------|
| `authentication.feature` | sign-up, login with e-mail and password, logout |
| `deployment.feature` | healthcheck endpoint |
| `registration.feature` | activation e-mail, activation link (expiry, reuse, tampering), resending, SMTP and Mailgun delivery and configuration |
| `posting.feature` | adding posts, 2000-character limit, images → WebP, 5 MiB limit, formats |
| `wall.feature` | wall, 3 tiles per row, 250 characters, thumbnail, category link, lightbox |
| `forum.feature` | forum, topics = categories, categories from the admin panel |
| `hashtags.feature` | hashtag links, hashtag page sorted by date |
| `markdown.feature` | Markdown rendering and HTML sanitisation |
| `i18n.feature` | Polish and English versions |
| `lightbox.feature` | lightbox in the browser |
| `chat_presence.feature` | online users by status, status changes, search by nick |
| `chat_messages.feature` | direct messages, 250-character limit, no Markdown, images → WebP, 5 MiB limit, privacy |
| `chat_groups.feature` | groups, links, join requests, adding / removing / muting members, rooms |
| `chat_browser.feature` | side panel, bubbles at the bottom, room tabs, mute countdown in the browser |

## Translations

```bash
python manage.py makemessages -l pl -l en --ignore=features
python manage.py makemessages -d djangojs -l pl -l en --ignore=staticfiles
python manage.py compilemessages
```

## Project structure

```
config/     settings (e-mail in email.py, Mailgun backend in mailgun.py, database in database.py),
            root URLs, healthcheck
accounts/   user model (e-mail login), sign-up with e-mail activation, profile, profile list
posts/      categories, posts, images (WebP conversion), hashtags, Markdown, wall, forum
chat/       messenger: presence, direct and group conversations, rooms, messages, join requests
templates/  HTML templates
static/     CSS (light blue / light green theme) and JS (lightbox, character counter, messenger)
locale/     translations (pl, en)
features/   BDD tests
```
