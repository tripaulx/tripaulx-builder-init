"""Composite blocks (item cards, step cards, bullet lists) built from components."""

from __future__ import annotations

from .components import arrow, card, icon_tile, step_number
from .svg import Svg


def item_card(
    svg: Svg,
    x: float,
    y: float,
    w: float,
    title: str,
    sub: str,
    *,
    tone: str = "brand",
    h: float = 76,
) -> None:
    """Card with a symbol tile, a title and one secondary line."""
    card(svg, x, y, w, h)
    icon_tile(svg, x + 18, y + (h - 40) / 2, tone)
    svg.text(x + 74, y + h / 2 - 4, title, size=16, weight=600, tracking=-0.012)
    svg.text(x + 74, y + h / 2 + 18, sub, size=14, fill="fg2")


def step_card(
    svg: Svg,
    x: float,
    y: float,
    w: float,
    step: tuple[str, str, str, str],
    *,
    tone: str = "brand",
    h: float = 150,
) -> None:
    """Numbered flow step: number, title, monospace detail and a caption."""
    number, title, detail, caption = step
    card(svg, x, y, w, h)
    step_number(svg, x + 33, y + 34, number, tone)
    svg.text(x + 58, y + 40, title, size=16, weight=600, tracking=-0.012)
    if detail:
        svg.text(x + 20, y + 82, detail, size=13, mono=True, fill="brand")
    for index, line in enumerate(caption.split("\n")):
        svg.text(x + 20, y + 112 + index * 20, line, size=14, fill="fg2")


def step_row(
    svg: Svg,
    y: float,
    steps: list[tuple[str, str, str, str]],
    *,
    x0: float = 64,
    total: float = 1152,
    gap: float = 24,
    h: float = 150,
) -> list[float]:
    """Lay out step cards in a row joined by arrows; return their centre x."""
    width = (total - gap * (len(steps) - 1)) / len(steps)
    centres = []
    for index, step in enumerate(steps):
        x = x0 + index * (width + gap)
        step_card(svg, x, y, width, step, h=h)
        centres.append(x + width / 2)
        if index:
            arrow(svg, [(x - gap + 6, y + h / 2), (x - 6, y + h / 2)])
    return centres


def bullets(
    svg: Svg,
    x: float,
    y: float,
    lines: list[str],
    *,
    tone: str = "fg3",
    size: float = 15,
) -> None:
    """Vertical list of short lines with a small dot marker."""
    for index, line in enumerate(lines):
        top = y + index * (size + 12)
        svg.add(
            f'<circle cx="{x + 3}" cy="{top - size * 0.32}" r="3" '
            f'fill="var(--{tone})"/>'
        )
        svg.text(x + 16, top, line, size=size, fill="fg2")


def caption(svg: Svg, x: float, y: float, label: str) -> None:
    """Small uppercase caption (DS kicker style)."""
    svg.text(x, y, label.upper(), size=12, weight=600, fill="fg3", tracking=0.06)
