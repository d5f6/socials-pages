from __future__ import annotations

import re
from io import BytesIO

import pytest
from PIL import Image

from socials_pages.__main__ import main
from socials_pages.build import build
from socials_pages.content import ContentError


def make_photo(path, orientation: int = 1) -> None:
    """200x100 JPEG, left half red and right half blue, with GPS data."""
    image = Image.new("RGB", (200, 100), "blue")
    image.paste("red", (0, 0, 100, 100))
    exif = Image.Exif()
    exif[0x0112] = orientation
    exif[0x8825] = {1: "N", 2: (52.0, 31.0, 0.0)}  # GPSInfo
    image.save(path, "JPEG", exif=exif, quality=95)


def test_build_writes_page_and_assets(write_config, tmp_path):
    config = write_config(
        """
        name: Dennis Freitag
        bio: Hallo
        links:
          - url: mastodon.social/@dennis
          - url: https://example.org/?a=1&b=2
            label: "<script>alert(1)</script>"
          - url: https://example.org/hidden
            hidden: true
        """
    )
    out = tmp_path / "_site"
    build(config, out)

    assert sorted(p.name for p in out.iterdir()) == ["favicon.svg", "index.html", "style.css"]
    html = (out / "index.html").read_text()
    assert "<title>Dennis Freitag</title>" in html
    assert '<meta name="description" content="Hallo">' in html
    assert "default-src &#39;none&#39;" not in html  # CSP meta is literal, not escaped
    assert "default-src 'none'" in html
    assert re.search(r'href="https://mastodon.social/@dennis" rel="me"><svg [^>]*>.*?<span>Mastodon</span>', html)
    assert 'href="https://example.org/?a=1&amp;b=2"' in html
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "example.org/hidden" not in html
    assert '<div class="avatar avatar-fallback" aria-hidden="true">DF</div>' in html
    assert re.search(r'href="style.css\?v=[0-9a-f]{12}"', html)


def test_avatar_is_square_webp_without_metadata(write_config, tmp_path):
    make_photo(tmp_path / "foto.jpg", orientation=6)  # rotate 90° clockwise
    out = tmp_path / "_site"
    build(write_config("name: D\navatar: foto.jpg\n"), out)

    html = (out / "index.html").read_text()
    assert re.search(r'<img class="avatar" src="avatar.webp\?v=[0-9a-f]{12}"', html)
    assert "avatar-fallback" not in html
    with Image.open(BytesIO((out / "avatar.webp").read_bytes())) as avatar:
        assert (avatar.format, avatar.size) == ("WEBP", (512, 512))
        assert "exif" not in avatar.info
        assert len(avatar.getexif()) == 0
        rgb = avatar.convert("RGB")
        # The orientation was applied: the red half is now on top.
        top, bottom = rgb.getpixel((256, 60)), rgb.getpixel((256, 450))
        assert top[0] > 200 and top[2] < 60
        assert bottom[2] > 200 and bottom[0] < 60


def test_unreadable_avatar_is_reported_and_nothing_is_written(write_config, tmp_path):
    (tmp_path / "foto.jpg").write_text("kein Bild")
    out = tmp_path / "_site"
    with pytest.raises(ContentError) as info:
        build(write_config("name: D\navatar: foto.jpg\n"), out)
    assert [(p.line, p.message) for p in info.value.problems] == [(2, "avatar: Die Datei ist kein lesbares Bild.")]
    assert not out.exists()


def test_cli_reports_errors(write_config, tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    config = write_config("links:\n  - url: ftp://example.org\n")
    assert main([str(config), "--out", str(tmp_path / "_site")]) == 1
    assert f"{config}:2: Link 1: url: Erlaubt sind" in capsys.readouterr().err


def test_cli_emits_github_annotations(write_config, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    config = write_config("links:\n  - url: ftp://example.org\n    label: 100%\n")
    assert main([str(config), "--out", str(tmp_path / "_site")]) == 1
    assert capsys.readouterr().out.startswith(f"::error file={config},line=2::Link 1: url: Erlaubt sind")


def test_cli_builds(write_config, tmp_path, capsys):
    config = write_config("links:\n  - url: example.org\n")
    assert main([str(config), "-o", str(tmp_path / "_site")]) == 0
    assert "1 Links" in capsys.readouterr().out
