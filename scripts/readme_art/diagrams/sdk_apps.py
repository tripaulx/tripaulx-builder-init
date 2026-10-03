"""The apps inside tripaulx-sdk and what each one is responsible for."""

from __future__ import annotations

from ..components import badge, badge_width, card, header, icon_tile
from ..content import load_copy
from ..svg import Svg

NAME = "sdk-apps"
SIZE = (1280, 660)

STATUS_TONE = {"ready": "success", "progress": "orange", "planned": "neutral"}
ICON_TONE = {"ready": "brand", "progress": "orange", "planned": "neutral"}

APPS = [
    ("core", "ready", 0),
    ("tenants", "ready", 1),
    ("accounts", "progress", 2),
    ("settings", "ready", 3),
    ("mail", "progress", 4),
    ("storage", "planned", 5),
    ("ai", "planned", 6),
    ("legal", "planned", 7),
]

STRINGS = load_copy(NAME)

PLANNED_PHASE = {"storage": 0, "ai": 1, "legal": 2}
COLS, GAP, TOP, CARD_H = 4, 24, 200, 196


def draw(theme: str, lang: str) -> Svg:
    """Draw the grid of SDK apps."""
    t = STRINGS[lang]
    svg = Svg(*SIZE, theme)
    header(svg, *t["head"])
    width = (1152 - GAP * (COLS - 1)) / COLS
    for name, status, index in APPS:
        x = 64 + (index % COLS) * (width + GAP)
        y = TOP + (index // COLS) * (CARD_H + GAP)
        label = t["status"][status]
        if status == "planned":
            label = t["phase"][PLANNED_PHASE[name]]
        _app_card(svg, x, y, width, name, label, status, t["lines"][index])
    return svg


def _app_card(
    svg: Svg,
    x: float,
    y: float,
    w: float,
    name: str,
    label: str,
    status: str,
    lines: tuple[str, str],
) -> None:
    """One app: symbol tile, status badge, module path and two lines."""
    card(svg, x, y, w, CARD_H)
    icon_tile(svg, x + 20, y + 20, ICON_TONE[status], size=44)
    tone = STATUS_TONE[status]
    label_w = badge_width(label, dot=True)
    badge(svg, x + w - 20 - label_w, y + 29, label, tone, dot=True)
    svg.text(x + 20, y + 102, name, size=22, weight=600, tracking=-0.018)
    svg.text(x + 20, y + 126, f"tripaulx.{name}", size=13, mono=True, fill="brand")
    svg.text(x + 20, y + 156, lines[0], size=14.5, fill="fg2")
    svg.text(x + 20, y + 178, lines[1], size=14.5, fill="fg2")
