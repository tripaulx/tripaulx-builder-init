# Documentos legais (`tripaulx.legal`)

Documentos legais e de governança versionados, servidos como HTML sanitizado:

- catálogo fechado: só slugs registrados são resolvidos, e uma requisição nunca escolhe um caminho de arquivo;
- modelos genéricos em inglês e pt-BR, com placeholders `{{ chave }}` preenchidos pela configuração;
- arquivos do projeto substituem os modelos, em qualquer idioma;
- termos de uso e política de privacidade num endpoint **público**; documentos de governança numa área **restrita**.

Versão em inglês: [../legal.md](../legal.md).

> Os textos distribuídos são **modelos**, não aconselhamento jurídico. Submeta
> os termos de uso e a política de privacidade à revisão de um advogado antes
> de ir ao ar.

## Ligação

`tripaulx.settings.apps` instala `tripaulx.legal` (o app não tem models). O
template de projeto já monta as rotas:

```python
# config/urls.py (espaços de trabalho)
urlpatterns += [
    path("api/v1/legal/", include("tripaulx.legal.api.urls")),  # restrita
    path("api/legal/public/", include("tripaulx.legal.api.urls_public")),
]

# config/urls_public.py (domínio principal)
urlpatterns += [
    path("api/legal/public/", include("tripaulx.legal.api.urls_public")),
]
```

## Catálogo

| Slug | Público | Categoria |
|---|---|---|
| `terms-of-use` | público | Políticas |
| `privacy-policy` | público | Políticas (LGPD + GDPR) |
| `risk-matrix` | restrito | Governança |
| `incident-response-plan` | restrito | Governança |
| `incident-register` | restrito | Registros |
| `incident-record-template` | restrito | Registros |
| `data-inventory` | restrito | Inventário |
| `governance-backlog` | restrito | Arquitetura |

Cada entrada é um `LegalDocument(slug, title, description, filename, category,
audience)`. Slugs seguem `[a-z0-9][a-z0-9-]*`, nomes de arquivo são caminhos
relativos simples (sem `..`, sem caminho absoluto), e todo arquivo resolvido
precisa ficar dentro da sua pasta de conteúdo (`Path.is_relative_to`); um
symlink apontando para fora é ignorado.

Registre mais documentos, ou remova alguns, na configuração:

```python
TRIPAULX = {
    "LEGAL_EXTRA_DOCUMENTS": [
        {
            "slug": "cookie-policy",
            "title": "Política de cookies",
            "description": "Cookies e armazenamento local que usamos.",
            "filename": "cookie-policy.md",
            "category": "Políticas",
            "audience": "public",
        },
    ],
    "LEGAL_EXCLUDED_DOCUMENTS": ["governance-backlog"],
}
```

Uma entrada extra com um slug existente substitui a original.

## Conteúdo e idiomas

O arquivo de um documento é o primeiro encontrado em:

1. cada pasta de `LEGAL_CONTENT_DIRS`: `<idioma>/<arquivo>` (`pt_BR/`, depois `pt/`), `<arquivo>`, depois `en/<arquivo>`;
2. os modelos do SDK: `<idioma>/<arquivo>`, depois `en/<arquivo>`.

O idioma é o da requisição (`LocaleMiddleware`, `Accept-Language`). Um arquivo
do projeto sempre vence um modelo do SDK, mesmo em outro idioma. Os modelos vão
dentro do wheel (`tripaulx/legal/content/`); encontre-os com
`tripaulx.legal.services.package_content_root()`.

## Placeholders

Os modelos usam `{{ company }}`, `{{ product }}`, `{{ company_id }}`,
`{{ company_address }}`, `{{ contact_email }}`, `{{ security_email }}`,
`{{ security_owner }}`, `{{ dpo_name }}`, `{{ dpo_email }}`,
`{{ jurisdiction }}`, `{{ data_location }}` e `{{ effective_date }}`. Eles são
preenchidos a partir de `TRIPAULX["LEGAL_CONTEXT"]` antes da renderização;
`company` e `product` usam `APP_NAME` quando vazios. Seus próprios documentos
podem usar qualquer outra chave.

Um placeholder sem valor (ausente ou vazio) continua visível, dentro de
`<span class="legal-placeholder">`, para que um documento inacabado nunca
pareça pronto. Liste-os, por idioma, antes de ir ao ar (o comando sai com erro
enquanto restar algum):

```bash
uv run python manage.py legal_check
uv run python manage.py legal_check --language pt-br
```

## Renderização e sanitização

Um subconjunto de Markdown escrito à mão: títulos, parágrafos, listas,
citações, blocos de código, linhas horizontais, tabelas, `**negrito**`,
`*itálico*`, `~~riscado~~`, `` `código` `` e links. Camadas:

1. tags HTML cruas são removidas da fonte;
2. todo texto é escapado; links só ficam para `http`, `https`, `mailto`,
   `/caminho` e `#âncora` (nada de `javascript:`, `data:` ou `//host`);
3. o resultado passa pela allowlist de tags e atributos do `nh3`;
4. links externos ganham `rel="noopener noreferrer"` e `target="_blank"`.

Tabelas ganham ganchos de CSS para o frontend: `legal-table-wrap`,
`legal-table` (`legal-table--has-ids` quando a primeira coluna é `ID`),
`legal-id`, `legal-badge legal-badge-<nível>` em volta de células que citam uma
gravidade, e `legal-score` em números sob colunas de pontuação. As palavras de
gravidade vêm de `LEGAL_BADGE_WORDS` (inglês e pt-BR por padrão, comparadas sem
caixa nem acentos); os cabeçalhos de pontuação, de `LEGAL_SCORE_COLUMNS`.

## Acesso

Documentos públicos: qualquer pessoa, no domínio principal e em todo espaço de
trabalho, sem autenticação (um token vencido nunca vira 401).

Documentos restritos exigem um usuário autenticado, ativo e com e-mail
verificado, num schema de `LEGAL_SCHEMAS` (vazio: todo espaço), que seja **ou**
administrador do espaço (`is_workspace_admin`: proprietário ou administrador)
**ou** tenha e-mail de um domínio de `LEGAL_ALLOWED_EMAIL_DOMAINS`. O domínio
precisa ser idêntico: `x@example.com.attacker.test` e `x@sub.example.com` não
são `example.com`.

## API

| Método e caminho | Acesso | Resposta |
|---|---|---|
| `GET /api/v1/legal/` | restrito | `{"documents": [{slug, title, description, category, audience}]}` (todos) |
| `GET /api/v1/legal/<slug>/` | restrito | `{slug, title, description, category, html}` |
| `GET /api/legal/public/` | qualquer um | os documentos públicos |
| `GET /api/legal/public/<slug>/` | qualquer um | `{slug, title, description, category, html}` |

- Respostas restritas levam `Cache-Control: private, no-store`; as públicas,
  `public, max-age=<LEGAL_PUBLIC_CACHE_SECONDS>` e `Vary: Accept-Language`.
  Todas levam `X-Content-Type-Options: nosniff`.
- Slug desconhecido (ou slug restrito no endpoint público): `404`.
- Documento registrado cujo arquivo não pode ser lido: `503`.
- Títulos, descrições e categorias seguem o idioma da requisição.

## Configuração

| Chave | Padrão | Significado |
|---|---|---|
| `LEGAL_CONTENT_DIRS` | `()` | pastas do projeto consultadas antes dos modelos do SDK |
| `LEGAL_CONTEXT` | `{}` | valores dos placeholders |
| `LEGAL_EXTRA_DOCUMENTS` | `()` | entradas extras do catálogo (dicts ou `LegalDocument`) |
| `LEGAL_EXCLUDED_DOCUMENTS` | `()` | slugs removidos do catálogo |
| `LEGAL_SCHEMAS` | `()` | schemas que servem documentos restritos (vazio: todos) |
| `LEGAL_ALLOWED_EMAIL_DOMAINS` | `()` | domínios de e-mail exatos aceitos além dos administradores |
| `LEGAL_PUBLIC_CACHE_SECONDS` | `3600` | `max-age` dos endpoints públicos |
| `LEGAL_BADGE_WORDS` | en + pt-BR | `{nível: (palavras, ...)}` dos badges de tabela |
| `LEGAL_SCORE_COLUMNS` | en + pt-BR | palavras de cabeçalho das colunas de pontuação |

O template as define a partir das variáveis `APP_LEGAL_*` em
`config/settings/base_parts/legal.py`, com `legal/` como pasta de conteúdo
(veja `legal/README.md` num projeto gerado).
