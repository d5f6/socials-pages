"""Read and validate socials.yml.

Every problem is collected (with its line number where possible) so a single
build run reports all mistakes at once. Messages are German because they are
shown to the page owner, who edits the file in the GitHub web editor.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from . import platforms

MAX_URL = 500
MAX_LABEL = 80
MAX_NAME = 80
MAX_BIO = 300

PAGE_KEYS = ("name", "bio", "avatar", "links")
LINK_KEYS = ("url", "label", "platform", "hidden")

EMAIL = re.compile(r"[^@\s/:]+@[^@\s/:]+\.[^@\s/:]+")


@dataclass(frozen=True)
class Problem:
    message: str
    line: int | None = None


class ContentError(Exception):
    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("\n".join(p.message for p in problems))
        self.problems = problems


@dataclass(frozen=True)
class Link:
    platform: str
    label: str
    url: str


@dataclass(frozen=True)
class Page:
    name: str
    bio: str
    avatar: Path | None
    avatar_line: int | None
    links: tuple[Link, ...]  # visible links only, in file order


def normalize_url(raw: str) -> str:
    """Accept http(s) and mailto links; add https:// or mailto: when missing."""
    value = raw.strip()
    if not value:
        raise ValueError("Bitte eine Adresse angeben.")
    if len(value) > MAX_URL:
        raise ValueError(f"Die Adresse darf höchstens {MAX_URL} Zeichen haben.")
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("Die Adresse darf keine Leer- oder Steuerzeichen enthalten.")

    if value.lower().startswith("mailto:"):
        if not EMAIL.fullmatch(value[7:]):
            raise ValueError("Das ist keine gültige E-Mail-Adresse.")
        return "mailto:" + value[7:]
    if "://" not in value:
        if EMAIL.fullmatch(value):
            return "mailto:" + value
        value = "https://" + value

    parts = urlsplit(value)
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError("Erlaubt sind nur https://-, http://- und E-Mail-Adressen.")
    try:
        parts.port  # raises for malformed ports
    except ValueError:
        raise ValueError("Die Adresse ist ungültig.") from None
    host = parts.hostname or ""
    if "." not in host or parts.username is not None:
        raise ValueError("Die Adresse ist ungültig.")
    return value


def load(path: Path) -> Page:
    data, key_lines, link_lines = _read(path)
    problems: list[Problem] = []

    def check(line: int | None, prefix: str, parse, *args, default=None):
        try:
            return parse(*args)
        except ValueError as exc:
            problems.append(Problem(f"{prefix}{exc}", line))
            return default

    for key in data:
        if key not in PAGE_KEYS:
            problems.append(Problem(_unknown_key(key, PAGE_KEYS), key_lines.get(str(key))))

    name = check(key_lines.get("name"), "name: ", _single_line, data.get("name"), MAX_NAME, default="")
    bio = check(key_lines.get("bio"), "bio: ", _bio, data.get("bio"), default="")
    avatar = check(key_lines.get("avatar"), "avatar: ", _avatar, data.get("avatar"), path.parent)

    links: list[Link] = []
    raw_links = data.get("links")
    if raw_links is None:
        raw_links = []
    if not isinstance(raw_links, list):
        problems.append(Problem("links: Jeder Link beginnt mit „- url: …“ in einer eigenen Zeile.", key_lines.get("links")))
        raw_links = []
    for number, item in enumerate(raw_links, start=1):
        line = link_lines[number - 1] if number <= len(link_lines) else None
        prefix = f"Link {number}: "
        if not isinstance(item, dict):
            problems.append(Problem(f"{prefix}Jeder Link braucht eine Zeile „url: …“.", line))
            continue
        for key in item:
            if key not in LINK_KEYS:
                problems.append(Problem(prefix + _unknown_key(key, LINK_KEYS), line))
        if "url" not in item:
            problems.append(Problem(f"{prefix}Die Zeile „url: …“ fehlt.", line))
            continue
        link = check(line, prefix, _link, item)
        hidden = check(line, prefix + "hidden: ", _flag, item.get("hidden"), default=False)
        if link is not None and not hidden:
            links.append(link)

    if problems:
        raise ContentError(problems)
    return Page(name=name, bio=bio, avatar=avatar, avatar_line=key_lines.get("avatar"), links=tuple(links))


def _read(path: Path) -> tuple[dict[Any, Any], dict[str, int], list[int]]:
    """Parse the YAML file and remember the lines of top-level keys and links."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ContentError([Problem(f"{path} gibt es nicht.")]) from None
    except UnicodeDecodeError:
        raise ContentError([Problem("Die Datei muss UTF-8-kodiert sein.")]) from None

    loader = yaml.SafeLoader(text)
    try:
        node = loader.get_single_node()
        data = loader.construct_document(node) if node is not None else None
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        detail = getattr(exc, "problem", None) or "Syntaxfehler"
        line = mark.line + 1 if mark is not None else None
        hint = "Prüfe Einrückung und Doppelpunkte; Text mit „: “ oder „#“ in Anführungszeichen setzen."
        raise ContentError([Problem(f"Die Datei ist kein gültiges YAML ({detail}). {hint}", line)]) from None
    finally:
        loader.dispose()

    if data is None:
        return {}, {}, []
    if not isinstance(data, dict) or not isinstance(node, yaml.MappingNode):
        raise ContentError([Problem("Die Datei muss aus Feldern wie „name:“ und „links:“ bestehen.", 1)])

    key_lines: dict[str, int] = {}
    link_lines: list[int] = []
    for key_node, value_node in node.value:
        key_lines[str(key_node.value)] = key_node.start_mark.line + 1
        if key_node.value == "links" and isinstance(value_node, yaml.SequenceNode):
            link_lines = [item.start_mark.line + 1 for item in value_node.value]
    return data, key_lines, link_lines


def _unknown_key(key: object, allowed: tuple[str, ...]) -> str:
    message = f"Unbekanntes Feld „{key}“."
    close = difflib.get_close_matches(str(key), allowed, n=1)
    if close:
        return f"{message} Meintest du „{close[0]}“?"
    return f"{message} Erlaubt sind: {', '.join(allowed)}."


def _text(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        # YAML turns e.g. `yes`, `2024` or `1.10` into non-text values.
        raise ValueError("Das muss Text sein. Setze den Wert in Anführungszeichen.")
    return value


def _single_line(value: object, limit: int) -> str:
    text = " ".join(_text(value).split())
    if len(text) > limit:
        raise ValueError(f"Höchstens {limit} Zeichen.")
    return text


def _bio(value: object) -> str:
    bio = "\n".join(line.strip() for line in _text(value).strip().splitlines())
    if len(bio) > MAX_BIO:
        raise ValueError(f"Höchstens {MAX_BIO} Zeichen.")
    return bio


def _avatar(value: object, root: Path) -> Path | None:
    name = _text(value).strip()
    if not name:
        return None
    root = root.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Das Bild muss im Repository liegen.")
    if not path.is_file():
        raise ValueError(f"Die Datei „{name}“ gibt es nicht (Groß- und Kleinschreibung beachten).")
    return path


def _flag(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError("Erlaubt sind true und false.")
    return value


def _platform(value: object) -> str | None:
    key = _text(value).strip().lower()
    if not key:
        return None
    if key not in platforms.PLATFORMS:
        message = f"Unbekannte Plattform „{key}“."
        close = difflib.get_close_matches(key, platforms.PLATFORMS, n=1)
        hint = f" Meintest du „{close[0]}“?" if close else " Die Namen stehen in socials_pages/platforms.py."
        raise ValueError(message + hint)
    return key


def _link(item: dict[Any, Any]) -> Link:
    errors: list[str] = []
    url = label = ""
    platform = None
    try:
        url = normalize_url(_text(item.get("url")))
    except ValueError as exc:
        errors.append(f"url: {exc}")
    try:
        label = _single_line(item.get("label"), MAX_LABEL)
    except ValueError as exc:
        errors.append(f"label: {exc}")
    try:
        platform = _platform(item.get("platform"))
    except ValueError as exc:
        errors.append(f"platform: {exc}")
    if errors:
        raise ValueError(" ".join(errors))
    platform = platform or platforms.detect(url)
    return Link(platform=platform, label=label or platforms.default_label(platform, url), url=url)
