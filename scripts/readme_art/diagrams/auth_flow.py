"""Sign-up to signed-in: workspace creation, verification and second factors."""

from __future__ import annotations

from ..blocks import caption, item_card, step_row
from ..components import badge, badge_width, header, panel
from ..content import load_copy
from ..svg import Svg

NAME = "auth-flow"
SIZE = (1280, 640)

STRINGS = load_copy(NAME)


def draw(theme: str, lang: str) -> Svg:
    """Draw the account flow diagram."""
    t = STRINGS[lang]
    svg = Svg(*SIZE, theme)
    header(svg, *t["head"])
    width = badge_width(t["badge"], dot=True)
    badge(svg, 1216 - width, 96, t["badge"], "success", dot=True)
    step_row(svg, 200, t["steps"], h=162)
    panel(svg, 64, 396, 1152, 210)
    caption(svg, 88, 432, t["factors"])
    card_w = (1152 - 48 - 32) / 3
    for index, (title, sub, tone) in enumerate(t["cards"]):
        x = 88 + index * (card_w + 16)
        item_card(svg, x, 452, card_w, title, sub, tone=tone)
    svg.text(88, 576, t["note"], size=14, fill="fg2", italic=True)
    return svg
