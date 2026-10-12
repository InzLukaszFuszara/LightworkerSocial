"""Shared helpers for step definitions."""

import io
import os

from behave import register_type
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def _quoted(text):
    return text


# {name:Q} matches the text between double quotes in a step.
_quoted.pattern = r'[^"]*'
register_type(Q=_quoted)

CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "WEBP": "image/webp",
    "BMP": "image/bmp",
}


def make_image(name, image_format="PNG", size=(64, 48), color=(110, 193, 239)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=image_format)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=CONTENT_TYPES[image_format])


def make_animated_gif(name, frames=3):
    buf = io.BytesIO()
    colours = [(110, 193, 239), (127, 209, 143), (255, 255, 255)]
    images = [Image.new("RGB", (32, 32), colours[i % 3]) for i in range(frames)]
    images[0].save(buf, format="GIF", save_all=True, append_images=images[1:], duration=100, loop=0)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/gif")


def make_huge_png(name, min_bytes):
    """A PNG of random noise (incompressible) bigger than ``min_bytes``."""
    side = 1400
    while True:
        img = Image.frombytes("RGB", (side, side), os.urandom(side * side * 3))
        buf = io.BytesIO()
        img.save(buf, format="PNG", compress_level=0)
        if buf.tell() > min_bytes:
            return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")
        side += 200


def soup(response):
    return BeautifulSoup(response.content.decode(), "html.parser")


def tiles(response):
    return soup(response).select(".tiles > .tile")


def tile(response, number):
    found = tiles(response)
    assert len(found) >= number, f"Expected at least {number} tiles, found {len(found)}"
    return found[number - 1]
