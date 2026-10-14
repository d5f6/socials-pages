"""Avatar processing: square-crop, resize and drop all metadata."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_FILE_BYTES = 25 * 1024 * 1024  # GitHub's limit for uploads in the browser
MAX_PIXELS = 80_000_000  # below Pillow's decompression bomb warning
AVATAR_SIZE = 512
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


class ImageError(ValueError):
    pass


def make_avatar(path: Path) -> bytes:
    """Return a 512x512 WebP without EXIF (no camera or location data)."""
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ImageError("Das Bild darf höchstens 25 MB groß sein.")
    try:
        with Image.open(path) as source:
            if source.format not in ALLOWED_FORMATS:
                raise ImageError("Erlaubt sind JPEG, PNG, WebP und GIF.")
            width, height = source.size
            if width * height > MAX_PIXELS:
                raise ImageError("Das Bild hat zu viele Pixel.")
            # Apply the EXIF orientation before the metadata is discarded.
            image = ImageOps.exif_transpose(source)
            has_alpha = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")
            image = ImageOps.fit(image, (AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("Die Datei ist kein lesbares Bild.") from exc
    out = BytesIO()
    image.save(out, "WEBP", quality=85, method=6)
    return out.getvalue()
