"""How the SDK, the template, a project and CapRover fit together."""

from __future__ import annotations

from .. import font
from ..blocks import caption, item_card
from ..components import arrow, badge, header, panel
from ..content import load_copy
from ..svg import Svg

NAME = "architecture"
SIZE = (1280, 640)

STRINGS = load_copy(NAME)

COL_W, GAP, TOP = 300, 126, 200


def draw(theme: str, lang: str) -> Svg:
    """Draw the architecture diagram."""
    t = STRINGS[lang]
    svg = Svg(*SIZE, theme)
    header(svg, *t["head"])
    for index, (label, items) in enumerate(t["cols"]):
        x = 64 + index * (COL_W + GAP)
        panel(svg, x, TOP, COL_W, 330)
        caption(svg, x + 22, TOP + 34, label)
        for row, (title, sub, tone) in enumerate(items):
            item_card(
                svg, x + 16, TOP + 54 + row * 88, COL_W - 32, title, sub, tone=tone
            )
        if index:
            mid = TOP + 165
            arrow(svg, [(x - GAP + 8, mid), (x - 8, mid)])
            edge = t["edges"][index - 1]
            label_w = font.mono_width(edge, 12) + 20
            svg.add(
                f'<rect x="{x - GAP / 2 - label_w / 2:.1f}" y="{mid - 42}" '
                f'width="{label_w:.1f}" height="24" rx="12" fill="var(--brand-soft)"/>'
            )
            svg.text(x - GAP / 2, mid - 26, edge, size=12, mono=True,
                     fill="brand-soft-fg", anchor="middle")  # fmt: skip
    _loops(svg, t["loops"])
    return svg


def _loops(svg: Svg, loops: tuple[str, str, str, str]) -> None:
    """Footer explaining how projects keep receiving updates."""
    y = 566
    x = 64
    for title, command in (loops[:2], loops[2:]):
        width = badge(svg, x, y - 18, title, "success", dot=True)
        command_w = svg.text(x + width + 12, y, command, size=14, mono=True, fill="fg2")
        x += width + command_w + 56
