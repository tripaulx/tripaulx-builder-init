# Legal documents

This folder holds the project's own legal and governance documents. It is in
`TRIPAULX["LEGAL_CONTENT_DIRS"]` (`config/settings/base_parts/legal.py`), so
any file here **wins over** the generic template shipped with `tripaulx-sdk`.
This README itself is never served.

## Documents

| Slug | File | Audience |
|---|---|---|
| `terms-of-use` | `terms-of-use.md` | public |
| `privacy-policy` | `privacy-policy.md` | public |
| `risk-matrix` | `risk-matrix.md` | restricted |
| `incident-response-plan` | `incident-response-plan.md` | restricted |
| `incident-register` | `incident-register.md` | restricted |
| `incident-record-template` | `incident-record-template.md` | restricted |
| `data-inventory` | `data-inventory.md` | restricted |
| `governance-backlog` | `governance-backlog.md` | restricted |

- Public: `GET /api/legal/public/` and `/api/legal/public/<slug>/`, on the
  apex domain and on every workspace, without authentication.
- Restricted: `GET /api/v1/legal/` and `/api/v1/legal/<slug>/`, on
  workspaces, for workspace admins and users of `APP_LEGAL_ALLOWED_EMAIL_DOMAINS`.

## Overriding a document

The file is looked up in this order (first match wins):

1. `legal/<language>/<file>`, e.g. `legal/pt_BR/privacy-policy.md`
   (the request's language, from `Accept-Language`);
2. `legal/<file>`, for every language;
3. `legal/en/<file>`;
4. the SDK template in the request's language, then in English.

To start from the SDK text, copy it out of the installed package:

```bash
SDK_LEGAL="$(uv run python -c 'from tripaulx.legal.services import package_content_root as r; print(r())')"
mkdir -p legal/pt_BR && cp "$SDK_LEGAL/pt_BR/privacy-policy.md" legal/pt_BR/
```

The SDK texts are **templates**: have the terms of use and the privacy policy
reviewed by a lawyer before going live.

## Placeholders

Documents may use `{{ company }}`, `{{ product }}`, `{{ company_id }}`,
`{{ company_address }}`, `{{ contact_email }}`, `{{ security_email }}`,
`{{ security_owner }}`, `{{ dpo_name }}`, `{{ dpo_email }}`,
`{{ jurisdiction }}`, `{{ data_location }}` and `{{ effective_date }}`. Set
them with the `APP_LEGAL_*` variables of `.env.*` (or add keys to
`LEGAL_CONTEXT`). A placeholder without a value stays visible in the page.
Before going live:

```bash
uv run python manage.py legal_check
```

## Formatting

Documents are Markdown: headings, paragraphs, lists, quotes, code, tables,
`**bold**`, `*italic*`, `~~strike~~` and links (`http`, `https`, `mailto`,
`/path`, `#anchor`). Raw HTML is removed. Tables get CSS hooks for the
frontend: `legal-table`, `legal-id` (first column named `ID`), `legal-badge
legal-badge-<critical|high|medium|low>` (severity words such as "High" or
"Alto") and `legal-score` (numbers under score columns).

## More documents

Register extra documents in `config/settings/base_parts/legal.py`:

```python
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
```

`LEGAL_EXCLUDED_DOCUMENTS` removes catalog entries you do not use.
