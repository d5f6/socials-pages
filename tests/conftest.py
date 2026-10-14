from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def write_config(tmp_path: Path):
    def write(text: str) -> Path:
        path = tmp_path / "socials.yml"
        path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return path

    return write
