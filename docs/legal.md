# Legal documents (`tripaulx.legal`)

Versioned legal and governance documents, served as sanitized HTML:

- a closed catalog: only registered slugs resolve, and a request never chooses a file path;
- generic templates in English and pt-BR, with `{{ key }}` placeholders filled from settings;
- project files override the templates, in any language;
- terms of use and privacy policy on a **public** endpoint; governance documents in a **restricted** area.

Portuguese version: [pt-BR/legal.md](pt-BR/legal.md).

> The shipped texts are **templates**, not legal advice. Have the terms of use
> and the privacy policy reviewed by a lawyer before going live.

## Wiring

`tripaulx.settings.apps` installs `tripaulx.legal` (it has no models). The
project template already mounts the routes:

```python
# config/urls.py (workspaces)
urlpatterns += [
    path("api/v1/legal/", include("tripaulx.legal.api.urls")),  # restricted
    path("api/legal/public/", include("tripaulx.legal.api.urls_public")),
]

# config/urls_public.py (apex domain)
urlpatterns += [
    path("api/legal/public/", include("tripaulx.legal.api.urls_public")),
]
```

## Catalog

| Slug | Audience | Category |
|---|---|---|
| `terms-of-use` | public | Policies |
| `privacy-policy` | public | Policies (LGPD + GDPR aware) |
| `risk-matrix` | restricted | Governance |
| `incident-response-plan` | restricted | Governance |
| `incident-register` | restricted | Records |
| `incident-record-template` | restricted | Records |
| `data-inventory` | restricted | Inventory |
| `governance-backlog` | restricted | Architecture |

Each entry is a `LegalDocument(slug, title, description, filename, category,
audience)`. Slugs must match `[a-z0-9][a-z0-9-]*`, file names are plain
relative paths (no `..`, no absolute path), and every resolved file must stay
inside its content folder (`Path.is_relative_to`), so a symlink pointing
elsewhere is ignored.

Register more documents, or drop some, in settings:

```python
TRIPAULX = {
    "LEGAL_EXTRA_DOCUMENTS": [
        {
            "slug": "cookie-policy",
            "title": "Cookie policy",
            "description": "Cookies and local storage we use.",
            "filename": "cookie-policy.md",
            "category": "Policies",
            "audience": "public",
        },
    ],
    "LEGAL_EXCLUDED_DOCUMENTS": ["governance-backlog"],
}
```

An extra entry with an existing slug replaces it.

## Content and languages

The file of a document is the first match of:

1. each folder of `LEGAL_CONTENT_DIRS`: `<language>/<file>` (`pt_BR/`, then `pt/`), `<file>`, then `en/<file>`;
2. the SDK templates: `<language>/<file>`, then `en/<file>`.

The language is the request's (`LocaleMiddleware`, `Accept-Language`). A
project file always wins over an SDK template, even in another language. The
templates ship inside the wheel (`tripaulx/legal/content/`); find them with
`tripaulx.legal.services.package_content_root()`.

## Placeholders

Templates use `{{ company }}`, `{{ product }}`, `{{ company_id }}`,
`{{ company_address }}`, `{{ contact_email }}`, `{{ security_email }}`,
`{{ security_owner }}`, `{{ dpo_name }}`, `{{ dpo_email }}`,
`{{ jurisdiction }}`, `{{ data_location }}` and `{{ effective_date }}`. They
are filled from `TRIPAULX["LEGAL_CONTEXT"]` before rendering; `company` and
`product` fall back to `APP_NAME`. Your own documents may use any other key.

A placeholder without a value (missing or empty) stays visible, wrapped in
`<span class="legal-placeholder">`, so an unfinished document never looks
finished. List them, per language, before going live (it exits non-zero
while any is left):

```bash
uv run python manage.py legal_check
uv run python manage.py legal_check --language pt-br
```

## Rendering and sanitization

A hand-written Markdown subset: headings, paragraphs, lists, quotes, fenced
code, rules, pipe tables, `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``
and links. Layers:

1. raw HTML tags are stripped from the source;
2. all text is HTML-escaped; links are kept only for `http`, `https`,
   `mailto`, `/path` and `#anchor` (no `javascript:`, `data:` or `//host`);
3. the result goes through the `nh3` allowlist of tags and attributes;
4. external links get `rel="noopener noreferrer"` and `target="_blank"`.

Tables get CSS hooks for the frontend: `legal-table-wrap`, `legal-table`
(`legal-table--has-ids` when the first column is `ID`), `legal-id`,
`legal-badge legal-badge-<level>` around cells naming a severity, and
`legal-score` on numbers under score columns. Severity words come from
`LEGAL_BADGE_WORDS` (English and pt-BR by default, compared without case or
accents); score headers from `LEGAL_SCORE_COLUMNS`.

## Access

Public documents: anyone, on the apex domain and on every workspace, without
authentication (a stale token never turns them into a 401).

Restricted documents need a user who is authenticated, active and has a
verified e-mail, in a schema listed in `LEGAL_SCHEMAS` (empty: every
workspace), and who is **either** a workspace admin (`is_workspace_admin`:
owner or admin) **or** has an e-mail in `LEGAL_ALLOWED_EMAIL_DOMAINS`. The
domain must match exactly: `x@example.com.attacker.test` and
`x@sub.example.com` are not `example.com`.

## API

| Method and path | Access | Answer |
|---|---|---|
| `GET /api/v1/legal/` | restricted | `{"documents": [{slug, title, description, category, audience}]}` (all) |
| `GET /api/v1/legal/<slug>/` | restricted | `{slug, title, description, category, html}` |
| `GET /api/legal/public/` | anyone | the public documents |
| `GET /api/legal/public/<slug>/` | anyone | `{slug, title, description, category, html}` |

- Restricted answers carry `Cache-Control: private, no-store`; public ones
  `public, max-age=<LEGAL_PUBLIC_CACHE_SECONDS>` and `Vary: Accept-Language`.
  All carry `X-Content-Type-Options: nosniff`.
- Unknown slug (or a restricted slug on the public endpoint): `404`.
- A registered document whose file cannot be read: `503`.
- Titles, descriptions and categories follow the request language.

## Settings

| Key | Default | Meaning |
|---|---|---|
| `LEGAL_CONTENT_DIRS` | `()` | project folders searched before the SDK templates |
| `LEGAL_CONTEXT` | `{}` | placeholder values |
| `LEGAL_EXTRA_DOCUMENTS` | `()` | extra catalog entries (dicts or `LegalDocument`) |
| `LEGAL_EXCLUDED_DOCUMENTS` | `()` | slugs removed from the catalog |
| `LEGAL_SCHEMAS` | `()` | schemas serving restricted documents (empty: all) |
| `LEGAL_ALLOWED_EMAIL_DOMAINS` | `()` | exact e-mail domains allowed besides admins |
| `LEGAL_PUBLIC_CACHE_SECONDS` | `3600` | `max-age` of the public endpoints |
| `LEGAL_BADGE_WORDS` | en + pt-BR | `{level: (words, ...)}` for table badges |
| `LEGAL_SCORE_COLUMNS` | en + pt-BR | header words of score columns |

The template sets them from `APP_LEGAL_*` variables in
`config/settings/base_parts/legal.py`, with `legal/` as the content folder
(see `legal/README.md` in a generated project).
