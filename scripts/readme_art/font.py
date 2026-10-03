"""Inter (the DS typeface): text measurement and an embedded, subset web font.

SVGs shown through ``<img>`` cannot fetch fonts, so each file carries its own
``@font-face`` with a WOFF2 subset (only the glyphs it uses, ``wght`` axis
kept) as a data URI.
"""

from __future__ import annotations

import base64
from functools import lru_cache
import io
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONT_PATH = Path(__file__).parent / "fonts" / "InterVariable.woff2"
MONO_ADVANCE = 0.6  # em width of one monospace glyph


@lru_cache(maxsize=1)
def _variable_font() -> bytes:
    """Read the variable font once."""
    return FONT_PATH.read_bytes()


@lru_cache(maxsize=8)
def _instance(weight: int) -> TTFont:
    """Return a static instance at ``weight`` for width measurement."""
    font = TTFont(io.BytesIO(_variable_font()))
    return instancer.instantiateVariableFont(font, {"wght": weight, "opsz": 14})


def text_width(
    text: str, size: float, weight: int = 400, tracking: float = 0.0
) -> float:
    """Return the rendered width of ``text`` in px (``tracking`` in em)."""
    font = _instance(weight)
    cmap = font.getBestCmap()
    metrics = font["hmtx"].metrics
    units = font["head"].unitsPerEm
    advance = sum(metrics[cmap.get(ord(char), ".notdef")][0] for char in text)
    return advance * size / units + tracking * size * max(len(text) - 1, 0)


def mono_width(text: str, size: float) -> float:
    """Approximate the width of monospace ``text`` in px."""
    return len(text) * size * MONO_ADVANCE


def font_face(chars: str) -> str:
    """Return an ``@font-face`` rule embedding Inter subset to ``chars``."""
    font = TTFont(io.BytesIO(_variable_font()))
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = []
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=chars + " ")
    subsetter.subset(font)
    # Pin the optical-size axis and keep only the weights the DS uses.
    font = instancer.instantiateVariableFont(font, {"opsz": 14, "wght": (400, 700)})
    buffer = io.BytesIO()
    font.flavor = "woff2"
    font.save(buffer)
    data = base64.b64encode(buffer.getvalue()).decode()
    return (
        "@font-face{font-family:'Inter';font-weight:100 900;"
        f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
    )
