"""Command line entry point: python -m socials_pages [socials.yml] [--out _site]."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .build import build
from .content import ContentError, Problem


def _report(config: Path, problem: Problem) -> None:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Workflow command: shows up on the run page and next to the file.
        message = problem.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        location = f"file={config}" + (f",line={problem.line}" if problem.line else "")
        print(f"::error {location}::{message}")
    else:
        location = f"{config}:{problem.line}" if problem.line else str(config)
        print(f"{location}: {problem.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m socials_pages", description="Build the static link page.")
    parser.add_argument("config", nargs="?", default="socials.yml", type=Path, help="default: %(default)s")
    parser.add_argument("-o", "--out", default="_site", type=Path, help="output directory (default: %(default)s)")
    args = parser.parse_args(argv)
    try:
        page = build(args.config, args.out)
    except ContentError as exc:
        for problem in exc.problems:
            _report(args.config, problem)
        return 1
    print(f"{args.out / 'index.html'}: {len(page.links)} Links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
