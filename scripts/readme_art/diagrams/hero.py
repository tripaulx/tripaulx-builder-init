"""Hero banner: logo, headline in the brand gradient and stack pills."""

from __future__ import annotations

from .. import brand
from ..components import PAD_X, badge
from ..content import load_copy
from ..svg import Svg

NAME = "hero"
SIZE = (1280, 440)

STRINGS = load_copy(NAME)

PILLS = [
    ("Django 6.1", "brand"),
    ("django-tenants", "brand"),
    ("PostgreSQL schemas", "violet"),
    ("Copier", "neutral"),
    ("uv", "neutral"),
    ("CapRover", "success"),
]


def _slab(svg: Svg, cx: float, top: float, label: str, *, active: bool) -> None:
    """Draw one isometric slab (a schema) with its name on the top face."""
    w, h, depth = 150, 40, 16
    face = "brand-soft" if active else "surface"
    bottom = top + 2 * h
    for side, paint in ((-w, "muted"), (w, "border-strong")):
        svg.add(
            f'<path d="M{cx + side} {top + h} L{cx} {bottom} l0 {depth} '
            f'L{cx + side} {top + h + depth} z" fill="var(--{paint})" '
            'stroke="var(--border-strong)"/>'
        )
    svg.add(
        f'<path d="M{cx} {top} L{cx + w} {top + h} L{cx} {bottom} '
        f'L{cx - w} {top + h} z" fill="var(--{face})" '
        'stroke="var(--border-strong)" stroke-width="1.2"/>'
    )
    color = "brand-soft-fg" if active else "fg2"
    svg.text(cx, top + h + 6, label, size=17, mono=True, fill=color, anchor="middle")


def _schemas(svg: Svg) -> None:
    """Draw a decorative stack of schema layers under the brand symbol."""
    cx = 1030
    for top, label in ((300, "globex"), (222, "acme"), (144, "public")):
        _slab(svg, cx, top, label, active=label == "acme")
    svg.add(brand.symbol(cx - 34, 52, 68, "url(#brand-grad)"))


def draw(theme: str, lang: str) -> Svg:
    """Draw the hero for ``theme`` and ``lang``."""
    t = STRINGS[lang]
    svg = Svg(*SIZE, theme)
    svg.add(brand.logo(PAD_X, 56, 34))
    svg.text(PAD_X, 152, t["kicker"], size=13, weight=600, fill="fg3", tracking=0.08)
    svg.text(PAD_X, 212, t["line1"], size=52, weight=600, tracking=-0.025)
    svg.text(
        PAD_X, 270, t["line2"], size=52, weight=600, tracking=-0.025,
        fill="url(#brand-grad)", italic=True,
    )  # fmt: skip
    svg.text(PAD_X, 320, t["lead"], size=19, fill="fg2")
    svg.text(PAD_X, 348, t["lead2"], size=19, fill="fg2")
    x = PAD_X
    for label, tone in PILLS:
        x += badge(svg, x, 376, label, tone, dot=True) + 10
    _schemas(svg)
    return svg
