# Lightworker Social

Aplikacja społecznościowa w **Python / Django** (backend + frontend renderowany po stronie serwera)
z testami **BDD** (behave + behave-django) oraz wersjami językowymi **polską** i **angielską**.

## Funkcje

- **Konta** – rejestracja oraz logowanie przez **e-mail i hasło** (`accounts.User`, `USERNAME_FIELD = "email"`).
  Nazwa użytkownika służy tylko jako publiczny adres profilu (`/u/<nazwa>/`).
- **Profil z tablicą użytkownika** – nagłówek profilu (nazwa, „o mnie”, liczba wpisów) i tablica wpisów
  w postaci **kafelków, po 3 w wierszu** (na węższych ekranach 2 / 1). Każdy kafelek zawiera:
  - pierwsze **250 znaków** wpisu (tekst bez znaczników Markdown),
  - **miniaturkę pierwszego zdjęcia** wpisu (WebP 480×480),
  - **link do kategorii** wpisu (tematu forum),
  - po kliknięciu otwiera **lightbox** z pełną treścią i wszystkimi zdjęciami
    (bez JavaScriptu link prowadzi do strony wpisu).
- **Dodawanie wpisów** (`/posts/new/`):
  - maks. **2000 znaków** (walidacja w formularzu i w modelu, licznik znaków na żywo),
  - **wiele zdjęć**, każde maks. **5 MiB**, formaty **JPG, PNG, GIF, WebP** – wszystkie są
    **konwertowane do WebP** (animowane GIF-y pozostają animowane),
  - obowiązkowa **kategoria** zdefiniowana przez administratora w panelu `/admin/`,
  - obsługa **Markdown** (bezpiecznie sanityzowany przez *bleach*),
  - obsługa **#hashtagów** (również z polskimi znakami, np. `#spokój`).
- **Forum** (`/forum/`) – kategorie jako tematy (z liczbą wpisów i datą ostatniego wpisu);
  po kliknięciu tematu wyświetlają się kafelki z wpisami z tablic wszystkich użytkowników.
- **Hashtagi** (`/tags/<hashtag>/`) – wszystkie wpisy wszystkich użytkowników z danym hashtagiem,
  posortowane od najnowszego.
- **Języki** – polski (domyślny) i angielski; przełącznik PL/EN w nagłówku. Język jest też wybierany
  automatycznie na podstawie ustawień przeglądarki. Nazwa i opis kategorii są wspólne dla wszystkich języków.
- **Kolorystyka** jasnoniebieska i jasnozielona.

## Uruchomienie

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py createsuperuser        # logowanie e-mailem
python manage.py seed_demo              # (opcjonalnie) dane demo, hasło: demo-pass-123
python manage.py runserver
```

Następnie w panelu `http://127.0.0.1:8000/admin/` dodaj kategorie (Wpisy → Kategorie).

Zmienne środowiskowe dla produkcji: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_DB_PATH`, `DJANGO_MEDIA_ROOT`.

## Testy BDD

Scenariusze Gherkin znajdują się w katalogu `features/`, a definicje kroków w `features/steps/`.

```bash
python manage.py behave                 # wszystkie scenariusze
python manage.py behave --tags=-browser # bez testu w przeglądarce
```

Scenariusz `features/lightbox.feature` (`@browser`) sprawdza lightbox w prawdziwej przeglądarce
(Playwright + Chromium: `playwright install chromium` lub zmienna `CHROMIUM_PATH`).

| Plik | Zakres |
|------|--------|
| `authentication.feature` | rejestracja, logowanie e-mailem i hasłem, wylogowanie |
| `posting.feature` | dodawanie wpisów, limit 2000 znaków, zdjęcia → WebP, limit 5 MiB, formaty |
| `wall.feature` | tablica, kafelki 3 w wierszu, 250 znaków, miniaturka, link do kategorii, lightbox |
| `forum.feature` | forum, tematy = kategorie, kategorie z panelu administracyjnego |
| `hashtags.feature` | linki hashtagów, strona hashtagu sortowana wg daty |
| `markdown.feature` | renderowanie Markdown i sanityzacja HTML |
| `i18n.feature` | wersja polska i angielska |
| `lightbox.feature` | lightbox w przeglądarce |

## Tłumaczenia

```bash
python manage.py makemessages -l pl -l en --ignore=features
python manage.py compilemessages
```

## Struktura

```
config/     ustawienia i główne URL-e
accounts/   model użytkownika (logowanie e-mailem), rejestracja, profil, lista profili
posts/      kategorie, wpisy, zdjęcia (konwersja WebP), hashtagi, Markdown, tablica, forum
templates/  szablony HTML
static/     CSS (motyw jasnoniebieski/jasnozielony) i JS (lightbox, licznik znaków)
locale/     tłumaczenia (pl, en)
features/   testy BDD
```

---

**English:** Django social app with user profiles and walls (3 tiles per row: 250-char excerpt,
first image thumbnail, category link, lightbox with the full post), posts up to 2000 characters
with Markdown, #hashtags and multiple images (≤ 5 MiB, JPG/PNG/GIF/WebP converted to WebP),
admin-defined categories shown as forum topics, hashtag pages sorted by date, e-mail + password
login, Polish & English UI. Run `python manage.py behave` for the BDD suite.
