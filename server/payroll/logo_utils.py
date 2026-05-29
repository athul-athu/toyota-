from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

LOGO_FILENAMES = (
    "toyota-logo.png",
    "toyota-logo.jpg",
    "toyota-logo.jpeg",
    "toyota-logo.webp",
    "Toyota-logo.png",
    "toyota_logo.png",
    "toyota-logo.svg",
)


def _search_dirs() -> list[Path]:
    root = Path(settings.BASE_DIR).parent
    return [
        root / "admin-dash" / "public",
        Path(__file__).resolve().parent / "assets",
        Path(settings.BASE_DIR) / "static" / "images",
    ]


def find_toyota_logo_source() -> Path | None:
    for directory in _search_dirs():
        if not directory.is_dir():
            continue
        for name in LOGO_FILENAMES:
            path = directory / name
            if path.is_file():
                return path
        for path in sorted(directory.glob("toyota*.*")):
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                return path
    return None


def get_cached_logo_png_path() -> Path | None:
    """PNG for PDF embedding; converts SVG to cached PNG when needed."""
    source = find_toyota_logo_source()
    if not source:
        return None

    if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        return source

    cache_dir = Path(__file__).resolve().parent / "assets"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / "toyota-logo-cache.png"

    if cached.is_file() and cached.stat().st_mtime >= source.stat().st_mtime:
        return cached

    try:
        from reportlab.graphics import renderPM
        from svglib.svglib import svg2rlg

        drawing = svg2rlg(str(source))
        if drawing is None:
            logger.warning("Could not parse SVG logo: %s", source)
            return None
        renderPM.drawToFile(drawing, str(cached), fmt="PNG")
        return cached
    except Exception as exc:
        logger.exception("SVG to PNG conversion failed: %s", exc)
        return None


def find_toyota_logo_path() -> Path | None:
    """Raster logo path for ReportLab Image."""
    return get_cached_logo_png_path()
