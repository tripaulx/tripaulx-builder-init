"""Diagram copy (en and pt-BR), kept in TOML next to the code."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import tomllib

COPY_DIR = Path(__file__).parent / "copy"


@lru_cache
def load_copy(name: str) -> dict:
    """Return ``{lang: strings}`` for the diagram ``name``."""
    with (COPY_DIR / f"{name}.toml").open("rb") as handle:
        return tomllib.load(handle)
