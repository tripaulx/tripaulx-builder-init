# Contributing

Thanks for helping! This repository holds two things:
- the **tripaulx-sdk** package (`sdk/`);
- the **Copier template** (`template/`) that new projects are created from.

Questions? Open an issue or write to the maintainer, **Flavio Almeida Paulino**
([f1@tripaulx.com](mailto:f1@tripaulx.com?subject=%5Btripaulx-builder-init%5D)).

## Setup

Requirements: [uv](https://docs.astral.sh/uv/), PostgreSQL 16+ and GNU gettext (for translations).

```bash
uv sync
cd sdk && uv run pytest
```

The SDK tests connect to `127.0.0.1:5432` as your OS user by default. Override with
`DB_USER`, `DB_PASSWORD`, `DB_HOST` and `DB_PORT`.

## Before opening a pull request

```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_file_size.py
scripts/check_translations.sh
(cd sdk && uv run pytest)
scripts/render_example.sh && (cd example && ./start setup && ./start test)
```

## README diagrams

The diagrams are generated, so never edit the SVGs. Change their text in
`scripts/readme_art/copy/*.toml` or their drawing in `scripts/readme_art/diagrams/`,
then run `uv run --group docs python -m scripts.readme_art`.

## Rules
- Follow the code standards in [`CLAUDE.md`](CLAUDE.md):
  - PEP 8 and PEP 257, with type hints;
  - files of about 150 lines, 300 at most;
  - business logic in `services/`.
- Write code, identifiers, docs and commits in **English**.
  - Every user-facing string goes through `gettext` and gets a `pt_BR` translation.
- **Migrations must stay backwards compatible within a minor version.** Never remove or rename a field without discussing it in the PR.
- Add tests together with every change, and update [`CHANGELOG.md`](CHANGELOG.md).
- Never commit secrets, real customer data or personal data. CI runs gitleaks.

## Releases

1. Bump `sdk/src/tripaulx/__init__.py`.
2. Move the `Unreleased` changelog entries under the new version.
3. Tag `vX.Y.Z`.

The release workflow publishes to PyPI with Trusted Publishing.
