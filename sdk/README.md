# tripaulx-sdk

The shared foundation of tripaulx-builders Django projects. It provides:

- multi-tenant Django 6 with **workspaces** (django-tenants, one PostgreSQL schema each);
- accounts with mandatory 2FA, an authenticator app (TOTP) and passkeys;
- AI providers, agents and skills with cost tracking;
- governance and legal documents;
- encrypted object storage.

It ships an API and the Django admin. There is no frontend.

> Status: **pre-release (0.1.0.dev)**. See the
> [project repository](https://github.com/tripaulx/tripaulx-builder-init) and its
> Copier template to start a new project.

## Install

```bash
uv add tripaulx-sdk
```

## Maintainer

Flavio Almeida Paulino ([f1@tripaulx.com](mailto:f1@tripaulx.com?subject=%5Btripaulx-sdk%5D)).

## License

MIT
