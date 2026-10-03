"""DS components drawn on an :class:`~scripts.readme_art.svg.Svg`."""

from __future__ import annotations

import math

from . import brand, font
from .svg import Svg
from .tokens import TONES

PAD_X = 64


def card(svg: Svg, x: float, y: float, w: float, h: float, *, r: float = 14) -> None:
    """Surface card: white/near-black fill, subtle border, soft shadow."""
    svg.add(
        f'<rect class="card" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
        'filter="url(#shadow)"/>'
    )


def panel(svg: Svg, x: float, y: float, w: float, h: float, *, r: float = 20) -> None:
    """Sunken panel grouping several cards."""
    svg.add(f'<rect class="sunken" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/>')


def badge_width(label: str, *, dot: bool = False) -> float:
    """Width of a :func:`badge` without drawing it."""
    return font.text_width(label, 13, 500) + 22 + (16 if dot else 0)


def badge(
    svg: Svg, x: float, y: float, label: str, tone: str = "brand", *, dot: bool = False
) -> float:
    """Pill badge (soft background, tone text). ``y`` is the top. Return width."""
    solid, soft, soft_fg = TONES[tone]
    size, height = 13, 26
    offset = 16 if dot else 0
    width = badge_width(label, dot=dot)
    svg.add(
        f'<rect x="{x}" y="{y}" width="{width:.1f}" height="{height}" '
        f'rx="{height / 2}" fill="var(--{soft})"/>'
    )
    if dot:
        svg.add(f'<circle cx="{x + 15}" cy="{y + 13}" r="3.5" fill="var(--{solid})"/>')
    svg.text(x + 11 + offset, y + 17.5, label, size=size, weight=500, fill=soft_fg)
    return width


def header(svg: Svg, number: str, kicker: str, title: str, lead: str) -> None:
    """Section header: logo, numbered kicker, H1 title and lead line."""
    svg.add(brand.logo(svg.width - PAD_X - 103, 52, 24))
    width = svg.text(PAD_X, 70, number, size=13, weight=600, fill="brand")
    svg.text(
        PAD_X + width + 12, 70, kicker.upper(), size=13, weight=600, fill="fg3",
        tracking=0.06,
    )  # fmt: skip
    svg.text(PAD_X, 118, title, size=36, weight=600, tracking=-0.022)
    svg.text(PAD_X, 152, lead, size=18, fill="fg2")


def arrow(
    svg: Svg, points: list[tuple[float, float]], *, css: str = "flow", head: bool = True
) -> None:
    """Polyline arrow through ``points`` with a filled head at the end."""
    path = " ".join(
        f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(points)
    )
    svg.add(f'<path class="{css}" d="{path}" stroke-linejoin="round"/>')
    if head:
        (x1, y1), (x2, y2) = points[-2], points[-1]
        angle = math.atan2(y2 - y1, x2 - x1)
        tip = [
            (x2 + 1, y2),
            (x2 - 10 * math.cos(angle - 0.45), y2 - 10 * math.sin(angle - 0.45)),
            (x2 - 10 * math.cos(angle + 0.45), y2 - 10 * math.sin(angle + 0.45)),
        ]
        coords = " ".join(f"{px:.1f},{py:.1f}" for px, py in tip)
        color = "var(--brand)" if css == "flow" else "var(--fg3)"
        svg.add(f'<polygon points="{coords}" fill="{color}"/>')


def icon_tile(
    svg: Svg, x: float, y: float, tone: str = "brand", size: int = 40
) -> None:
    """Draw a rounded tile with the tripaulx symbol (app and step icons)."""
    _, soft, _ = TONES[tone]
    solid = TONES[tone][0]
    svg.add(
        f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="10" '
        f'fill="var(--{soft})"/>'
    )
    inner = size * 0.5
    offset = (size - inner) / 2
    svg.add(brand.symbol(x + offset, y + offset, inner, f"var(--{solid})"))


def step_number(
    svg: Svg, cx: float, cy: float, label: str, tone: str = "brand"
) -> None:
    """Draw a filled circle with a number, for ordered flows."""
    solid = TONES[tone][0]
    svg.add(f'<circle cx="{cx}" cy="{cy}" r="15" fill="var(--{solid})"/>')
    svg.text(cx, cy + 5, label, size=14, weight=700, fill="canvas", anchor="middle")


def check(svg: Svg, cx: float, cy: float, r: float = 13) -> None:
    """Success check mark inside a circle."""
    svg.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="var(--success)"/>')
    k = r / 13
    svg.add(
        f'<path d="M{cx - 5.5 * k} {cy}l{4 * k} {4 * k} {7.5 * k} {-8 * k}" '
        'stroke="var(--canvas)" stroke-width="2.4" fill="none" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )
