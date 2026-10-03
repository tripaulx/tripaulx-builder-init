"""Enforce the file-size convention: ~150 LOC per file, 300 at most.

Usage: python scripts/check_file_size.py [paths...]  (default: sdk template scripts)
Files over SOFT_LIMIT are reported as warnings; over HARD_LIMIT the run fails.
Migrations and lock files are ignored.
"""

from __future__ import annotations

from pathlib import Path
import sys

SOFT_LIMIT = 150
HARD_LIMIT = 300
SUFFIXES = {".py", ".jinja", ".sh"}
SKIP_PARTS = {"migrations", ".venv", "__pycache__", "node_modules"}


def iter_files(roots: list[Path]) -> list[Path]:
    """Return the source files under ``roots`` that the convention covers."""
    files: list[Path] = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or SKIP_PARTS.intersection(path.parts):
                continue
            if path.suffix in SUFFIXES:
                files.append(path)
    return files


def main(argv: list[str]) -> int:
    """Print oversize files; return 1 when any file exceeds the hard limit."""
    defaults = [Path("sdk"), Path("template"), Path("scripts")]
    roots = [Path(arg) for arg in argv] or defaults
    failed = False
    for path in iter_files(roots):
        lines = sum(1 for _ in path.open(encoding="utf-8"))
        if lines > HARD_LIMIT:
            print(f"ERROR {path}: {lines} lines (max {HARD_LIMIT})")
            failed = True
        elif lines > SOFT_LIMIT:
            print(f"warn  {path}: {lines} lines (aim for {SOFT_LIMIT})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
