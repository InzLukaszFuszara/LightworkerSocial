"""Markdown rendering, hashtag extraction and excerpts for posts."""

import html
import re

import bleach
import markdown
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

# A hashtag is "#" followed by letters/digits/underscore (Unicode aware, so
# "#zażółć" works), not preceded by a word character, "&" (HTML entities)
# or another "#".
HASHTAG_RE = re.compile(r"(?<![\w&#/])#(\w{1,50})", re.UNICODE)

ALLOWED_TAGS = {
    "p", "br", "hr", "strong", "em", "b", "i", "del", "s", "code", "pre",
    "blockquote", "ul", "ol", "li", "a", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tr", "th", "td", "sup", "sub", "abbr",
}
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "class", "rel"], "abbr": ["title"], "th": ["align"], "td": ["align"]}
ALLOWED_PROTOCOLS = {"http", "https", "mailto"}

MARKDOWN_EXTENSIONS = ["extra", "sane_lists", "nl2br"]

# Lines that start with "#word" would be headings in Python-Markdown; real
# headings need a space after the hashes ("# Title").
_LINE_START_HASHTAG = re.compile(r"^(\s{0,3})#(?=\w)", re.MULTILINE | re.UNICODE)
_TAG_SPLIT = re.compile(r"(<[^>]+>)")
_SKIP_TAGS = {"a", "code", "pre"}
_RENDERED_HASHTAG = re.compile(r'<a class="hashtag" href="[^"]*">#(\w+)</a>', re.UNICODE)


def normalise_tag(name):
    return name.lower()


def extract_hashtags(text):
    """Return the unique, lower-cased hashtags of ``text`` (in order).

    Only hashtags that are rendered as links count, so ``#words`` inside
    code blocks or link texts are ignored.
    """
    seen = []
    for tag in _RENDERED_HASHTAG.findall(render_markdown(text)):
        tag = normalise_tag(tag)
        if tag not in seen:
            seen.append(tag)
    return seen


def _link_hashtags(rendered_html):
    """Wrap hashtags found in text nodes (outside a/code/pre) with links."""
    parts = _TAG_SPLIT.split(rendered_html)
    depth = 0
    for i, part in enumerate(parts):
        if part.startswith("<"):
            m = re.match(r"<\s*(/)?\s*([a-zA-Z0-9]+)", part)
            if m and m.group(2).lower() in _SKIP_TAGS and not part.endswith("/>"):
                depth += -1 if m.group(1) else 1
                depth = max(depth, 0)
            continue
        if depth:
            continue

        def repl(match):
            tag = match.group(1)
            url = reverse("posts:hashtag", kwargs={"name": normalise_tag(tag)})
            return f'<a class="hashtag" href="{html.escape(url)}">#{tag}</a>'

        parts[i] = HASHTAG_RE.sub(repl, part)
    return "".join(parts)


def render_markdown(text):
    """Render user Markdown to sanitised HTML with clickable hashtags."""
    source = _LINE_START_HASHTAG.sub(r"\1\\#", text or "")
    rendered = markdown.markdown(source, extensions=MARKDOWN_EXTENSIONS, output_format="html")
    cleaned = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned = bleach.linkify(cleaned, skip_tags=["pre", "code"])
    return mark_safe(_link_hashtags(cleaned))


def plain_text(text):
    """Markdown source -> readable plain text (no markup)."""
    source = _LINE_START_HASHTAG.sub(r"\1\\#", text or "")
    rendered = markdown.markdown(source, extensions=MARKDOWN_EXTENSIONS)
    rendered = re.sub(r"<br\s*/?>|</(p|li|h\d|blockquote|pre|tr)>", " ", rendered)
    return re.sub(r"\s+", " ", html.unescape(strip_tags(rendered))).strip()


def excerpt(text, length):
    """First ``length`` characters of the plain text of a post."""
    plain = plain_text(text)
    if len(plain) <= length:
        return plain
    return plain[:length].rstrip() + "…"
