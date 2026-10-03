"""Roadmap timeline from the skeleton to the 0.1.0 release."""

from __future__ import annotations

from ..components import badge, badge_width, check, header
from ..content import load_copy
from ..svg import Svg

NAME = "roadmap"
SIZE = (1280, 430)
DONE = 7  # phases completed so far (7 = all, 0.1.0 released)

STRINGS = load_copy(NAME)

LINE_Y = 278


def draw(theme: str, lang: str) -> Svg:
    """Draw the roadmap timeline."""
    t = STRINGS[lang]
    svg = Svg(*SIZE, theme)
    header(svg, *t["head"])
    count = len(t["items"])
    step = 1032 / (count - 1)
    xs = [124 + index * step for index in range(count)]
    last = xs[min(DONE, count - 1)]
    svg.add(
        f'<path class="dash" d="M{last} {LINE_Y} L{xs[-1]} {LINE_Y}"/>'
        f'<path d="M{xs[0]} {LINE_Y} L{last} {LINE_Y}" stroke="var(--brand)" '
        'stroke-width="3" stroke-linecap="round"/>'
    )
    for index, (title, sub) in enumerate(t["items"]):
        _node(svg, xs[index], index, title, sub, t)
    return svg


def _node(svg: Svg, x: float, index: int, title: str, sub: str, t: dict) -> None:
    """One phase: marker on the line, label above, title and detail below."""
    if index < DONE:
        check(svg, x, LINE_Y, r=15)
    else:
        active = index == DONE
        stroke = "var(--orange)" if active else "var(--border-strong)"
        svg.add(
            f'<circle cx="{x}" cy="{LINE_Y}" r="14" fill="var(--surface)" '
            f'stroke="{stroke}" stroke-width="{3 if active else 1.5}"/>'
        )
        svg.text(
            x, LINE_Y + 5, str(index), size=13, weight=700, fill="fg2", anchor="middle"
        )
    if index == DONE:
        width = badge_width(t["next"], dot=True)
        badge(svg, x - width / 2, LINE_Y - 66, t["next"], "orange", dot=True)
    label = f"{t['phase']} {index}".upper()
    svg.text(x, LINE_Y + 48, label, size=12, weight=600, fill="fg3", anchor="middle",
             tracking=0.06)  # fmt: skip
    svg.text(
        x, LINE_Y + 76, title, size=17, weight=600, anchor="middle", tracking=-0.012
    )
    svg.text(x, LINE_Y + 100, sub, size=14, fill="fg2", anchor="middle")
