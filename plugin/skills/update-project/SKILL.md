---
name: update-project
description: Update an existing tripaulx-builders project to the latest tripaulx-builder-init template and tripaulx-sdk release (copier update, uv lock upgrade, migrations, tests). Use when the user wants to upgrade, update or sync a project that was created from the tripaulx template or depends on tripaulx-sdk.
argument-hint: "[template-version, e.g. v0.2.0]"
allowed-tools: Bash(git status*) Bash(git diff*) Bash(uvx copier *) Bash(uv lock *) Bash(uv sync*) Bash(./start *)
---

# Update a tripaulx-builders project

Run this from the project root. The root must contain `.copier-answers.yml`; if it
does not, the project was not generated from the template, so stop and explain.

Arguments: `$ARGUMENTS`. This is an optional template tag (for example `v0.2.0`). The
default is the latest tag.

## 1. Preconditions

- `git status --porcelain` must be empty. Copier needs a clean tree to compute and show its diff. If the tree is dirty, ask the user to commit or stash first; never stash on their behalf.
- Read `CHANGELOG.md` in the template repository for the versions between the project's `_commit` (in `.copier-answers.yml`) and the target. Summarise the changes for the user, breaking ones first: https://github.com/tripaulx/tripaulx-builder-init/blob/main/CHANGELOG.md

## 2. Template

```bash
uvx copier update --trust --defaults            # latest tag
uvx copier update --trust --defaults --vcs-ref v0.2.0   # a specific tag
```

- Resolve any conflict markers or `.rej` files. **Keep the project's own changes**, especially business apps, `PROJECT_*_APPS` and project-specific settings, and take the template's infrastructure changes.
- Show the user `git diff --stat` and the important hunks.

## 3. SDK

```bash
uv lock --upgrade-package tripaulx-sdk && uv sync
```

The template pins `tripaulx-sdk` to a minor range (for example `>=0.1,<0.2`). Moving
to the next minor version comes with the template update that changes that pin.

## 4. Verify

1. `./start setup` runs the migrations: shared schema, bootstrap, every workspace.
2. `./start test` must pass.
3. `uv run python manage.py makemigrations --check --dry-run` must report no changes.

If a new SDK migration would drop or rename a field, stop and show it to the user
before applying anything. Projects never lose data without explicit confirmation.

## 5. Hand over

Summarise what changed (template files, SDK version from → to, new environment
variables to add in CapRover). Offer to commit, with the message
`chore: update from tripaulx-builder-init <version>`.
