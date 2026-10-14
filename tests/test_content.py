from __future__ import annotations

import pytest

from socials_pages import platforms
from socials_pages.content import ContentError, Link, load, normalize_url


def problems(path) -> list[tuple[int | None, str]]:
    with pytest.raises(ContentError) as info:
        load(path)
    return [(p.line, p.message) for p in info.value.problems]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://example.org/path?q=1", "https://example.org/path?q=1"),
        ("  example.org  ", "https://example.org"),
        ("http://example.org", "http://example.org"),
        ("me@example.org", "mailto:me@example.org"),
        ("MAILTO:me@example.org", "mailto:me@example.org"),
    ],
)
def test_normalize_url_accepts(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "javascript:alert(1)",
        "JavaScript://example.org/%0aalert(1)",
        "data:text/html,hi",
        "ftp://example.org",
        "https://exa mple.org",
        "https://localhost",
        "https://user@example.org",
        "https://example.org:notaport",
        "mailto:not-an-address",
        "https://example.org/" + "x" * 500,
    ],
)
def test_normalize_url_rejects(raw):
    with pytest.raises(ValueError):
        normalize_url(raw)


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://mastodon.social/@dennis", "mastodon"),
        ("https://unknown-instance.example/@dennis", "mastodon"),
        ("https://bsky.app/profile/dennis.bsky.social", "bluesky"),
        ("https://www.linkedin.com/in/dennis", "linkedin"),
        ("https://twitter.com/dennis", "x"),
        ("https://open.spotify.com/user/1", "spotify"),
        ("https://notgithub.com/dennis", "website"),
        ("mailto:me@example.org", "email"),
    ],
)
def test_detect_platform(url, platform):
    assert platforms.detect(url) == platform


def test_every_platform_has_an_icon():
    for key in platforms.PLATFORMS:
        assert 'class="icon' in platforms.icon_svg(key)
        assert key in platforms.STROKE_ICONS or key in platforms._brand_paths(), key


def test_full_file(write_config):
    page = load(
        write_config(
            """
            name: "  Dennis   Freitag "
            bio: |
              Zeile eins
                Zeile zwei
            links:
              - url: mastodon.social/@dennis
              - url: https://github.com/d5f6
                label: Code
              - url: me@example.org
              - url: https://example.org/hidden
                hidden: true
              - url: https://social.example/@me
                platform: Pixelfed
            """
        )
    )
    assert page.name == "Dennis Freitag"
    assert page.bio == "Zeile eins\nZeile zwei"
    assert page.avatar is None
    assert page.links == (
        Link("mastodon", "Mastodon", "https://mastodon.social/@dennis"),
        Link("github", "Code", "https://github.com/d5f6"),
        Link("email", "me@example.org", "mailto:me@example.org"),
        Link("pixelfed", "Pixelfed", "https://social.example/@me"),
    )


def test_empty_values_are_allowed(write_config):
    page = load(write_config('name: ""\nbio:\navatar: ""\nlinks:\n  # - url: example.org\n'))
    assert (page.name, page.bio, page.avatar, page.links) == ("", "", None, ())
    assert load(write_config("")).links == ()


def test_reports_all_problems_with_line_numbers(write_config):
    path = write_config(
        """
        name: Dennis
        bio: yes
        links:
          - url: javascript:alert(1)
          - url: https://example.org
            lable: Typo
          - label: ohne url
          - url: https://example.org
            platform: mastadon
            hidden: vielleicht
        """
    )
    assert problems(path) == [
        (2, "bio: Das muss Text sein. Setze den Wert in Anführungszeichen."),
        (4, "Link 1: url: Die Adresse ist ungültig."),
        (5, "Link 2: Unbekanntes Feld „lable“. Meintest du „label“?"),
        (7, "Link 3: Die Zeile „url: …“ fehlt."),
        (8, "Link 4: platform: Unbekannte Plattform „mastadon“. Meintest du „mastodon“?"),
        (8, "Link 4: hidden: Erlaubt sind true und false."),
    ]


def test_unknown_top_level_key(write_config):
    assert problems(write_config("name: a\nlinkz: []\n")) == [(2, "Unbekanntes Feld „linkz“. Meintest du „links“?")]


def test_links_must_be_a_list(write_config):
    assert problems(write_config("links: https://example.org\n")) == [
        (1, "links: Jeder Link beginnt mit „- url: …“ in einer eigenen Zeile.")
    ]


def test_yaml_syntax_error(write_config):
    ((line, message),) = problems(write_config("name: a\nlinks:\n  - url: x\n   label: y\n"))
    assert line == 4
    assert message.startswith("Die Datei ist kein gültiges YAML")


def test_file_must_be_a_mapping(write_config):
    assert problems(write_config("- url: example.org\n")) == [
        (1, "Die Datei muss aus Feldern wie „name:“ und „links:“ bestehen.")
    ]


def test_length_limits(write_config):
    path = write_config(f"name: {'n' * 81}\nlinks:\n  - url: example.org\n    label: {'l' * 81}\n")
    assert problems(path) == [
        (1, "name: Höchstens 80 Zeichen."),
        (3, "Link 1: label: Höchstens 80 Zeichen."),
    ]


def test_avatar_must_exist_inside_the_repo(write_config, tmp_path):
    (tmp_path.parent / "outside.jpg").write_bytes(b"x")
    assert problems(write_config("avatar: ../outside.jpg\n")) == [(1, "avatar: Das Bild muss im Repository liegen.")]
    assert problems(write_config("avatar: Avatar.JPG\n")) == [
        (1, "avatar: Die Datei „Avatar.JPG“ gibt es nicht (Groß- und Kleinschreibung beachten).")
    ]
