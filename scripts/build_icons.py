"""Extract the brand icons socials-pages needs from a simple-icons npm package.

Usage:
    curl -sO https://registry.npmjs.org/simple-icons/-/simple-icons-<version>.tgz
    tar xzf simple-icons-<version>.tgz
    python scripts/build_icons.py package/

Writes socials_pages/icons.json ({slug: svg path data}). simple-icons is CC0.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from socials_pages.platforms import ICONS_FILE, PLATFORMS, SAFE_PATH, STROKE_ICONS  # noqa: E402

SVG = re.compile(
    r'<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
    r"<title>[^<]*</title><path d=\"([^\"]+)\"/></svg>"
)


def main(package_dir: str) -> int:
    icons_dir = Path(package_dir) / "icons"
    paths: dict[str, str] = {}
    missing: list[str] = []
    for slug in PLATFORMS:
        if slug in STROKE_ICONS:
            continue
        svg_file = icons_dir / f"{slug}.svg"
        if not svg_file.is_file():
            missing.append(slug)
            continue
        match = SVG.fullmatch(svg_file.read_text().strip())
        if not match or not SAFE_PATH.fullmatch(match.group(1)):
            print(f"unexpected SVG structure: {svg_file}", file=sys.stderr)
            return 1
        paths[slug] = match.group(1)
    if missing:
        print(f"no icon in simple-icons for: {', '.join(missing)}", file=sys.stderr)
        return 1
    ICONS_FILE.write_text(json.dumps(paths, indent=0, sort_keys=True) + "\n")
    print(f"wrote {len(paths)} icons to {ICONS_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
