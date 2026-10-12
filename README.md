# Lightworker Social

A social media application built with **Python / Django** (backend + server-rendered frontend),
with **BDD** tests (behave + behave-django) and **Polish** and **English** language versions.

## Features

- **Accounts** – sign-up and login with **e-mail and password** (`accounts.User`, `USERNAME_FIELD = "email"`).
  The username is only used as the public address of the profile (`/u/<username>/`).
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

## BDD tests

Gherkin scenarios live in the `features/` directory and step definitions in `features/steps/`.

```bash
python manage.py behave                 # all scenarios
python manage.py behave --tags=-browser # without the browser test
```

The `features/lightbox.feature` scenario (`@browser`) checks the lightbox in a real browser
(Playwright + Chromium: `playwright install chromium` or the `CHROMIUM_PATH` variable).

| File | Scope |
|------|-------|
| `authentication.feature` | sign-up, login with e-mail and password, logout |
| `posting.feature` | adding posts, 2000-character limit, images → WebP, 5 MiB limit, formats |
| `wall.feature` | wall, 3 tiles per row, 250 characters, thumbnail, category link, lightbox |
| `forum.feature` | forum, topics = categories, categories from the admin panel |
| `hashtags.feature` | hashtag links, hashtag page sorted by date |
| `markdown.feature` | Markdown rendering and HTML sanitisation |
| `i18n.feature` | Polish and English versions |
| `lightbox.feature` | lightbox in the browser |

## Translations

```bash
python manage.py makemessages -l pl -l en --ignore=features
python manage.py compilemessages
```

## Project structure

```
config/     settings and root URLs
accounts/   user model (e-mail login), sign-up, profile, profile list
posts/      categories, posts, images (WebP conversion), hashtags, Markdown, wall, forum
templates/  HTML templates
static/     CSS (light blue / light green theme) and JS (lightbox, character counter)
locale/     translations (pl, en)
features/   BDD tests
```
