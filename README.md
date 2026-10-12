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

Accounts created with `createsuperuser` or in the admin panel are active immediately.

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
| `registration.feature` | activation e-mail, activation link (expiry, reuse, tampering), resending, SMTP delivery and configuration |
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
config/     settings (incl. SMTP configuration in email.py) and root URLs
accounts/   user model (e-mail login), sign-up with e-mail activation, profile, profile list
posts/      categories, posts, images (WebP conversion), hashtags, Markdown, wall, forum
chat/       messenger: presence, direct and group conversations, rooms, messages, join requests
templates/  HTML templates
static/     CSS (light blue / light green theme) and JS (lightbox, character counter, messenger)
locale/     translations (pl, en)
features/   BDD tests
```
