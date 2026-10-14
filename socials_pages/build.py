"""Render socials.yml into a static site directory."""

from __future__ import annotations

import hashlib
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import content, images, platforms

PACKAGE = Path(__file__).parent
STATIC = PACKAGE / "static"


def _version(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def _initials(name: str) -> str:
    return "".join(word[0] for word in name.split()[:2]).upper()


def build(config: Path, out: Path) -> content.Page:
    """Validate config and write index.html plus assets into out.

    Raises content.ContentError when socials.yml or the avatar is invalid;
    nothing is written in that case.
    """
    page = content.load(config)
    avatar = None
    if page.avatar is not None:
        try:
            avatar = images.make_avatar(page.avatar)
        except images.ImageError as exc:
            raise content.ContentError([content.Problem(f"avatar: {exc}", page.avatar_line)]) from None

    # All URLs are relative so the page also works under
    # https://<user>.github.io/<repo>/ before a custom domain is set.
    assets = {path.name: path.read_bytes() for path in sorted(STATIC.iterdir())}
    if avatar is not None:
        assets["avatar.webp"] = avatar
    asset_urls = {name: f"{name}?v={_version(data)}" for name, data in assets.items()}

    env = Environment(
        loader=FileSystemLoader(PACKAGE / "templates"),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html = env.get_template("index.html").render(
        page=page,
        initials=_initials(page.name),
        asset=asset_urls.__getitem__,
        avatar_url=asset_urls.get("avatar.webp"),
        icon=platforms.icon_svg,
    )

    out.mkdir(parents=True, exist_ok=True)
    for name, data in assets.items():
        (out / name).write_bytes(data)
    (out / "index.html").write_text(html, encoding="utf-8")
    return page
