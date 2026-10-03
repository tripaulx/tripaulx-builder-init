"""Minimal SVG document builder themed with the DS tokens."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

from . import font, tokens

STYLE = """
.bg{fill:var(--canvas)}
.card{fill:var(--surface);stroke:var(--border-strong);stroke-width:1}
.sunken{fill:var(--sunken);stroke:var(--border);stroke-width:1}
.line{stroke:var(--border-strong);stroke-width:1.5;fill:none}
.flow{stroke:var(--brand);stroke-width:2;fill:none}
.dash{stroke:var(--fg3);stroke-width:1.5;fill:none;stroke-dasharray:5 6}
.logo{fill:var(--logo)}
text{font-family:%(sans)s;font-feature-settings:'cv11','ss01','ss03'}
.mono{font-family:%(mono)s}
"""


@dataclass
class Svg:
    """An SVG drawing for one theme; ``render`` embeds fonts and styles."""

    width: int
    height: int
    theme: str
    parts: list[str] = field(default_factory=list)
    chars: set[str] = field(default_factory=set)

    def add(self, markup: str) -> None:
        """Append raw SVG markup."""
        self.parts.append(markup)

    def color(self, token: str) -> str:
        """Return the hex value of ``token`` in this drawing's theme."""
        return tokens.THEMES[self.theme][token]

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float = 16,
        weight: int = 400,
        fill: str = "fg",
        anchor: str = "start",
        tracking: float = 0.0,
        mono: bool = False,
        italic: bool = False,
    ) -> float:
        """Draw one line of text; return its width in px."""
        if not mono:
            self.chars.update(value)
        paint = fill if fill.startswith("url(") else f"var(--{fill})"
        attrs = [
            f'x="{x:.1f}"',
            f'y="{y:.1f}"',
            f'font-size="{size}"',
            f'font-weight="{weight}"',
            f'fill="{paint}"',
            f'text-anchor="{anchor}"',
        ]
        if tracking:
            attrs.append(f'letter-spacing="{tracking * size:.2f}"')
        if mono:
            attrs.append('class="mono"')
        if italic:
            attrs.append('font-style="italic"')
        self.add(f"<text {' '.join(attrs)}>{escape(value)}</text>")
        if mono:
            return font.mono_width(value, size)
        return font.text_width(value, size, weight, tracking)

    def render(self, title: str) -> str:
        """Return the complete SVG document."""
        self.chars.update(title)
        style = STYLE % {"sans": tokens.SANS, "mono": tokens.MONO}
        variables = tokens.css_variables(self.theme)
        shadow = self.color("shadow")
        defs = (
            '<defs><linearGradient id="brand-grad" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{self.color("grad-from")}"/>'
            f'<stop offset="1" stop-color="{self.color("grad-to")}"/>'
            '</linearGradient><filter id="shadow" x="-10%" y="-10%" '
            'width="120%" height="140%"><feDropShadow dx="0" dy="2" '
            f'stdDeviation="4" flood-color="#000" flood-opacity="{shadow}"/>'
            "</filter></defs>"
        )
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
            f'role="img" aria-label="{escape(title)}">'
            f"<title>{escape(title)}</title>"
            f"<style>{font.font_face(''.join(sorted(self.chars)))}"
            f"svg{{{variables}}}{style}</style>{defs}"
        )
        background = (
            f'<rect class="bg" width="{self.width}" height="{self.height}" rx="28"/>'
        )
        return head + background + "".join(self.parts) + "</svg>"
