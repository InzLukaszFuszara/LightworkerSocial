"""Validation and WebP conversion of uploaded post images."""

import io
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

# Formats (as reported by Pillow) that may be uploaded.
ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}
ACCEPT_ATTR = "image/jpeg,image/png,image/gif,image/webp,.jpg,.jpeg,.png,.gif,.webp"
WEBP_QUALITY = 85


def validate_image_upload(uploaded, max_bytes=None):
    """Raise ``ValidationError`` unless ``uploaded`` is a JPG/PNG/GIF/WebP <= 5 MiB."""
    max_bytes = max_bytes or settings.POST_IMAGE_MAX_BYTES
    if uploaded.size > max_bytes:
        raise ValidationError(
            _("File %(name)s is too large (%(size)s). The maximum size is %(max)s."),
            code="file_too_large",
            params={
                "name": uploaded.name,
                "size": filesizeformat(uploaded.size),
                "max": filesizeformat(max_bytes),
            },
        )
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as img:
            image_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise ValidationError(
            _("File %(name)s is not a valid image."),
            code="invalid_image",
            params={"name": uploaded.name},
        )
    finally:
        uploaded.seek(0)
    if image_format not in ALLOWED_FORMATS:
        raise ValidationError(
            _("File %(name)s has an unsupported format. Allowed formats: JPG, PNG, GIF, WebP."),
            code="invalid_format",
            params={"name": uploaded.name},
        )


def _normalise_mode(img):
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    )
    return img.convert("RGBA" if has_alpha else "RGB")


def _webp_name():
    return f"{uuid.uuid4().hex}.webp"


def convert_to_webp(uploaded):
    """Return a ``ContentFile`` with ``uploaded`` re-encoded as WebP.

    Animated GIF/WebP files keep their animation.
    """
    uploaded.seek(0)
    with Image.open(uploaded) as img:
        out = io.BytesIO()
        if getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1:
            img.save(
                out,
                format="WEBP",
                save_all=True,
                quality=WEBP_QUALITY,
                loop=img.info.get("loop", 0),
                duration=img.info.get("duration", 100),
            )
        else:
            img = ImageOps.exif_transpose(img)
            _normalise_mode(img).save(out, format="WEBP", quality=WEBP_QUALITY, method=4)
    return ContentFile(out.getvalue(), name=_webp_name())


def make_thumbnail(webp_file):
    """Return a square-ish WebP thumbnail ``ContentFile`` of a stored image file."""
    webp_file.seek(0)
    with Image.open(webp_file) as img:
        img.seek(0)
        thumb = _normalise_mode(img.copy())
    thumb = ImageOps.fit(thumb, settings.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    out = io.BytesIO()
    thumb.save(out, format="WEBP", quality=80)
    return ContentFile(out.getvalue(), name=_webp_name())
