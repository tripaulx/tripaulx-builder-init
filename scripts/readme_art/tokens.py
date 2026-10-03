"""tripaulx design-system tokens, converted from OKLCH to sRGB hex.

Light uses the warm ``ink`` neutrals on a cream canvas; dark uses chroma-free
neutrals on pure black, with the brighter brand stops (blue-400, violet-400).
"""

from __future__ import annotations

LIGHT: dict[str, str] = {
    "canvas": "#fdf8f2",
    "surface": "#ffffff",
    "sunken": "#efeae3",
    "muted": "#e7e2db",
    "fg": "#101113",
    "fg2": "#6c6864",
    "fg3": "#a8a49e",
    "border": "#e7e2db",
    "border-strong": "#d7d2cc",
    "brand": "#00748e",
    "brand-soft": "#d3f8ff",
    "brand-soft-fg": "#004f61",
    "violet": "#4f42c9",
    "violet-soft": "#e1e5ff",
    "violet-soft-fg": "#261d6c",
    "success": "#00a245",
    "success-soft": "#d6fad6",
    "success-soft-fg": "#004f22",
    "orange": "#fb6e00",
    "orange-soft": "#ffe1c7",
    "orange-soft-fg": "#6c2000",
    "grad-from": "#009dbb",
    "grad-to": "#5e55e1",
    "logo": "#000000",
    "shadow": "0.06",
}

DARK: dict[str, str] = {
    "canvas": "#000000",
    "surface": "#070707",
    "sunken": "#000000",
    "muted": "#141414",
    "fg": "#f5f5f5",
    "fg2": "#cecece",
    "fg3": "#989898",
    "border": "#1b1b1b",
    "border-strong": "#292929",
    "brand": "#50e5ff",
    "brand-soft": "#002830",
    "brand-soft-fg": "#a7efff",
    "violet": "#7776f5",
    "violet-soft": "#160f41",
    "violet-soft-fg": "#c0c7ff",
    "success": "#18d459",
    "success-soft": "#002f12",
    "success-soft-fg": "#a4faa7",
    "orange": "#ff811a",
    "orange-soft": "#421102",
    "orange-soft-fg": "#ffba84",
    "grad-from": "#50e5ff",
    "grad-to": "#7776f5",
    "logo": "#ffffff",
    "shadow": "0",
}

THEMES = {"light": LIGHT, "dark": DARK}

# Tones usable by badges, dots and accents: (solid, soft background, soft text).
TONES: dict[str, tuple[str, str, str]] = {
    "brand": ("brand", "brand-soft", "brand-soft-fg"),
    "violet": ("violet", "violet-soft", "violet-soft-fg"),
    "success": ("success", "success-soft", "success-soft-fg"),
    "orange": ("orange", "orange-soft", "orange-soft-fg"),
    "neutral": ("fg2", "muted", "fg2"),
}

SANS = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
MONO = "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"


def css_variables(theme: str) -> str:
    """Return ``--name: value;`` declarations for one theme."""
    tokens = THEMES[theme]
    return "".join(f"--{name}:{value};" for name, value in tokens.items())
