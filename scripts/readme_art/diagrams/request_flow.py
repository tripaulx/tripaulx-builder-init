"""How one request travels from a subdomain to its workspace schema."""

from __future__ import annotations

from ..blocks import bullets, caption, step_row
from ..components import arrow, header, panel
from ..content import load_copy
from ..svg import Svg

NAME = "request-flow"
SIZE = (1280, 720)

STRINGS = load_copy(NAME)

DB_TOP = 420


def draw(theme: str, lang: str) -> Svg:
    """Draw the request flow diagram."""
    t = STRINGS[lang]
    svg = Svg(*SIZE, theme)
    header(svg, *t["head"])
    centres = step_row(svg, 200, t["steps"], h=162)
    panel(svg, 64, DB_TOP, 1152, 252)
    caption(svg, 88, DB_TOP + 36, t["db"])
    width = (1152 - 48 - 48) / 3
    for index, (name, host, lines) in enumerate(t["schemas"]):
        x = 88 + index * (width + 24)
        _schema_card(
            svg, x, DB_TOP + 58, width, name, host, lines, active=name == "acme"
        )
    target = 88 + width + 24 + width / 2
    arrow(
        svg,
        [(centres[-1], 362), (centres[-1], 392), (target, 392), (target, DB_TOP + 52)],
    )
    return svg


def _schema_card(
    svg: Svg,
    x: float,
    y: float,
    w: float,
    name: str,
    host: str,
    lines: list[str],
    *,
    active: bool,
) -> None:
    """Draw a schema: its name, the host that reaches it and what it stores."""
    stroke = "var(--brand)" if active else "var(--border-strong)"
    fill = "var(--brand-soft)" if active else "var(--surface)"
    svg.add(
        f'<rect x="{x}" y="{y}" width="{w}" height="170" rx="14" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{2 if active else 1}" filter="url(#shadow)"/>'
    )
    svg.text(x + 22, y + 38, name, size=20, mono=True, fill="fg", weight=600)
    svg.text(x + w - 22, y + 37, host, size=12, mono=True, fill="fg3", anchor="end")
    bullets(svg, x + 22, y + 82, lines, tone="brand" if active else "fg3")
