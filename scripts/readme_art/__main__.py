"""Build every README diagram: ``python -m scripts.readme_art``."""

from __future__ import annotations

from pathlib import Path
import sys

from . import brand
from .diagrams import architecture, auth_flow, hero, request_flow, roadmap, sdk_apps

DIAGRAMS = [hero, architecture, request_flow, sdk_apps, auth_flow, roadmap]
OUTPUT = Path("docs/assets/readme")


def write_logos() -> None:
    """Write the standalone logo in black (light theme) and white (dark theme)."""
    for theme, color in (("light", "#000000"), ("dark", "#ffffff")):
        markup = brand.logo(0, 0, brand.LOGO_HEIGHT).replace(
            'class="logo"', f'fill="{color}"'
        )
        (OUTPUT / f"logo-{theme}.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="tripaulx" '
            f'width="{brand.LOGO_WIDTH}" height="{brand.LOGO_HEIGHT}" '
            f'viewBox="0 0 {brand.LOGO_WIDTH} {brand.LOGO_HEIGHT}">{markup}</svg>'
        )


def main(names: list[str]) -> None:
    """Write ``<name>-<lang>-<theme>.svg`` for every diagram (or ``names``)."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_logos()
    for module in DIAGRAMS:
        if names and module.NAME not in names:
            continue
        for lang in module.STRINGS:
            for theme in ("light", "dark"):
                svg = module.draw(theme, lang)
                path = OUTPUT / f"{module.NAME}-{lang}-{theme}.svg"
                path.write_text(svg.render(module.STRINGS[lang]["title"]))
                print(f"wrote {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
