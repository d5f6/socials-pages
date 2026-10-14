"""Supported platforms, URL-based detection and inline SVG icons."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from urllib.parse import urlsplit

from markupsafe import Markup

ICONS_FILE = Path(__file__).with_name("icons.json")


@dataclass(frozen=True)
class Platform:
    title: str
    hosts: tuple[str, ...] = ()


# Keys double as simple-icons slugs (see scripts/build_icons.py), except for
# the entries drawn in STROKE_ICONS below.
PLATFORMS: dict[str, Platform] = {
    "website": Platform("Webseite"),
    "email": Platform("E-Mail"),
    "mastodon": Platform(
        "Mastodon",
        (
            "mastodon.social",
            "mastodon.online",
            "mastodon.de",
            "chaos.social",
            "troet.cafe",
            "norden.social",
            "social.tchncs.de",
            "det.social",
            "mstdn.social",
            "fosstodon.org",
            "hachyderm.io",
            "infosec.exchange",
        ),
    ),
    "bluesky": Platform("Bluesky", ("bsky.app",)),
    "pixelfed": Platform("Pixelfed", ("pixelfed.social", "pixelfed.de")),
    "peertube": Platform("PeerTube"),
    "lemmy": Platform("Lemmy"),
    "misskey": Platform("Misskey", ("misskey.io",)),
    "matrix": Platform("Matrix", ("matrix.to",)),
    "github": Platform("GitHub", ("github.com",)),
    "gitlab": Platform("GitLab", ("gitlab.com",)),
    "codeberg": Platform("Codeberg", ("codeberg.org",)),
    "linkedin": Platform("LinkedIn", ("linkedin.com",)),
    "xing": Platform("XING", ("xing.com",)),
    "x": Platform("X (Twitter)", ("x.com", "twitter.com")),
    "threads": Platform("Threads", ("threads.net", "threads.com")),
    "instagram": Platform("Instagram", ("instagram.com",)),
    "facebook": Platform("Facebook", ("facebook.com", "fb.com")),
    "youtube": Platform("YouTube", ("youtube.com", "youtu.be")),
    "tiktok": Platform("TikTok", ("tiktok.com",)),
    "twitch": Platform("Twitch", ("twitch.tv",)),
    "vimeo": Platform("Vimeo", ("vimeo.com",)),
    "discord": Platform("Discord", ("discord.gg", "discord.com")),
    "reddit": Platform("Reddit", ("reddit.com",)),
    "telegram": Platform("Telegram", ("t.me", "telegram.me")),
    "signal": Platform("Signal", ("signal.me",)),
    "whatsapp": Platform("WhatsApp", ("wa.me", "whatsapp.com")),
    "snapchat": Platform("Snapchat", ("snapchat.com",)),
    "tumblr": Platform("Tumblr", ("tumblr.com",)),
    "pinterest": Platform("Pinterest", ("pinterest.com", "pinterest.de")),
    "flickr": Platform("Flickr", ("flickr.com",)),
    "behance": Platform("Behance", ("behance.net",)),
    "dribbble": Platform("Dribbble", ("dribbble.com",)),
    "medium": Platform("Medium", ("medium.com",)),
    "substack": Platform("Substack", ("substack.com",)),
    "devdotto": Platform("DEV", ("dev.to",)),
    "hashnode": Platform("Hashnode", ("hashnode.com", "hashnode.dev")),
    "stackoverflow": Platform("Stack Overflow", ("stackoverflow.com",)),
    "keybase": Platform("Keybase", ("keybase.io",)),
    "orcid": Platform("ORCID", ("orcid.org",)),
    "researchgate": Platform("ResearchGate", ("researchgate.net",)),
    "spotify": Platform("Spotify", ("spotify.com",)),
    "soundcloud": Platform("SoundCloud", ("soundcloud.com",)),
    "bandcamp": Platform("Bandcamp", ("bandcamp.com",)),
    "lastdotfm": Platform("Last.fm", ("last.fm",)),
    "steam": Platform("Steam", ("steamcommunity.com", "steampowered.com")),
    "itchdotio": Platform("itch.io", ("itch.io",)),
    "playstation": Platform("PlayStation"),
    "strava": Platform("Strava", ("strava.com",)),
    "komoot": Platform("komoot", ("komoot.com", "komoot.de")),
    "letterboxd": Platform("Letterboxd", ("letterboxd.com",)),
    "goodreads": Platform("Goodreads", ("goodreads.com",)),
    "printables": Platform("Printables", ("printables.com",)),
    "thingiverse": Platform("Thingiverse", ("thingiverse.com",)),
    "patreon": Platform("Patreon", ("patreon.com",)),
    "kofi": Platform("Ko-fi", ("ko-fi.com",)),
    "buymeacoffee": Platform("Buy Me a Coffee", ("buymeacoffee.com",)),
    "paypal": Platform("PayPal", ("paypal.me", "paypal.com")),
    "rss": Platform("RSS-Feed"),
}

# Outline icons for generic entries and for brands simple-icons does not ship
# (LinkedIn was removed there at the brand owner's request).
STROKE_ICONS: dict[str, str] = {
    "website": (
        "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18Z M3.5 12h17"
        " M12 3c2.4 2.4 3.6 5.4 3.6 9s-1.2 6.6-3.6 9c-2.4-2.4-3.6-5.4-3.6-9s1.2-6.6 3.6-9Z"
    ),
    "email": "M3.5 6h17v12h-17Z M3.5 7l8.5 6.5L20.5 7",
    "linkedin": "M4 8h16v11H4Z M9 8V6a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2 M4 13h16",
    "link": (
        "M10 13.5a4 4 0 0 0 5.7.3l3-3a4 4 0 0 0-5.7-5.6l-1.2 1.2"
        " M14 10.5a4 4 0 0 0-5.7-.3l-3 3a4 4 0 0 0 5.7 5.6l1.2-1.2"
    ),
}
FALLBACK_ICON = "link"

_SVG = '<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="{d}"/></svg>'
SAFE_PATH = re.compile(r"[0-9MmLlHhVvCcSsQqTtAaZzEe.,\-\s]+")


@cache
def _brand_paths() -> dict[str, str]:
    paths = json.loads(ICONS_FILE.read_text())
    # Paths end up unescaped in the page, so only accept plain path data.
    return {key: d for key, d in paths.items() if SAFE_PATH.fullmatch(d)}


def icon_svg(key: str) -> Markup:
    if key in STROKE_ICONS:
        return Markup(_SVG.format(cls="icon icon-stroke", d=STROKE_ICONS[key]))
    path = _brand_paths().get(key)
    if path is None:
        return icon_svg(FALLBACK_ICON)
    return Markup(_SVG.format(cls="icon", d=path))


def _host(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")


def detect(url: str) -> str:
    if url.lower().startswith("mailto:"):
        return "email"
    host = _host(url)
    for key, platform in PLATFORMS.items():
        if any(host == h or host.endswith("." + h) for h in platform.hosts):
            return key
    # Most fediverse profiles on unknown instances look like https://host/@name.
    if urlsplit(url).path.startswith("/@"):
        return "mastodon"
    return "website"


def default_label(platform: str, url: str) -> str:
    if platform == "email":
        return url.split(":", 1)[1]
    if platform == "website":
        return _host(url)
    return PLATFORMS[platform].title
