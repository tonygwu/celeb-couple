"""A link with no unfurl tags posts as a bare URL.

Twitter, LinkedIn and Slack all read og: and twitter: meta tags. Without them a
post shows the raw address with no title, description or picture, and LinkedIn
suppresses reach on top of that. A sibling project shipped without these and
found out on the day.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BOARD = (REPO / "web/board.html").read_text()
DEPLOY = (REPO / "scripts/deploy_site.sh").read_text()

REQUIRED = ["og:type", "og:title", "og:description", "og:url", "og:image",
            "og:image:width", "og:image:height", "og:image:alt",
            "twitter:card", "twitter:title", "twitter:description", "twitter:image"]


@pytest.mark.parametrize("tag", REQUIRED)
def test_the_tag_is_present(tag):
    assert f'"{tag}"' in BOARD


def test_the_card_type_shows_a_picture():
    assert 'content="summary_large_image"' in BOARD


def test_the_card_image_exists_and_is_the_right_size():
    """og:image pointing at a 404 unfurls worse than having no tag."""
    png = REPO / "web/og.png"
    assert png.exists(), "run scripts/render_og.sh"
    head = png.read_bytes()[:26]
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    w = int.from_bytes(head[16:20], "big")
    h = int.from_bytes(head[20:24], "big")
    assert (w, h) == (1200, 630), f"{w}x{h}; Twitter wants 1200x630"


def test_the_deploy_stages_the_image_and_refuses_without_it():
    assert "cp \"$OG\" site/og.png" in DEPLOY
    assert "REFUSING: web/og.png is missing" in DEPLOY


def test_every_absolute_url_in_the_tags_is_the_live_host():
    """A localhost or file:// URL in og:image is the classic way this breaks."""
    for m in re.findall(r'(?:property|name)="(?:og|twitter):(?:url|image)"\s+content="([^"]+)"', BOARD):
        assert m.startswith("https://celebrities.tonygwu.com/"), m


def test_the_description_is_a_usable_length():
    m = re.search(r'name="description" content="([^"]+)"', BOARD)
    assert m, "no meta description"
    assert 80 <= len(m.group(1)) <= 300, len(m.group(1))


def test_the_page_still_has_a_doctype_and_a_viewport():
    """The sibling project shipped without either and rendered in quirks mode
    with text clipped off the right edge on a phone."""
    assert BOARD.lstrip().lower().startswith("<!doctype html>")
    assert 'name="viewport"' in BOARD
    assert "@media (max-width:560px)" in BOARD


def test_the_card_carries_no_scores_so_it_cannot_go_stale():
    """The image is static on purpose. A card quoting a name or a number needs
    regenerating on every refresh, and will silently stop matching the board."""
    card = (REPO / "web/og-card.html").read_text()
    assert not re.search(r"[+−-]\d+\.\d\d", card), "the card quotes a score"


def test_the_card_type_survives_a_compact_thumbnail():
    """LinkedIn and Slack often render a ~255px thumbnail, about 21% scale.
    The first card had a 19px eyebrow, 27px body and 16px chips, which came out
    at 4.0, 5.7 and 3.4px - only the headline was readable. Nothing under 42px
    earns its place on this image."""
    card = (REPO / "web/og-card.html").read_text()
    sizes = [int(m) for m in re.findall(r"font-size:(\d+)px", card)]
    assert sizes, "no font sizes found; the selector changed"
    too_small = [s for s in sizes if s < 42]
    assert not too_small, (
        f"{too_small} would render under 9px in a 255px thumbnail")
