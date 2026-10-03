# Armazenamento de objetos (`tripaulx.storage`)

Armazenamento de objetos privado e compatível com S3, para projetos multi-tenant:

- toda chave de objeto fica sob `tenants/<schema>/`, e chaves de outro tenant são recusadas;
- os arquivos são cifrados na aplicação antes do upload (envelope encryption, AES-256-GCM);
- os uploads passam por uma política configurável: lista de tipos MIME conferida pelos bytes mágicos, limites de tamanho e limite de pixels para imagens.

Funciona com o AWS S3 e com provedores compatíveis com S3 (endereçamento por caminho, SigV4).

## Instalação

O app já está nas listas de apps padrão do SDK. As dependências de execução são um extra opcional:

```bash
uv add "tripaulx-sdk[storage]"   # boto3, cryptography, pillow
```

Importar `tripaulx.storage` nunca exige essas dependências. Usar o cliente sem elas levanta `ImproperlyConfigured`, com o comando de instalação na mensagem.

## Configuração

Todas as opções ficam em `settings.TRIPAULX`. O template do projeto lê as variáveis de ambiente em `config/settings/base_parts/object_storage.py`.

| Chave | Env (template) | Padrão | Significado |
|---|---|---|---|
| `S3_ENABLED` | ligado quando as duas chaves existem | `False` | Desligado: toda chamada levanta `StorageError` |
| `S3_ENDPOINT_URL` | `APP_S3_ENDPOINT_URL` | `""` | Endpoint do provedor (vazio = AWS) |
| `S3_REGION` | `APP_S3_REGION` | `""` | Região do bucket |
| `S3_BUCKET` | `APP_S3_BUCKET` | `""` | Nome do bucket privado |
| `S3_ACCESS_KEY` | `APP_S3_ACCESS_KEY` | `""` | Id da chave de acesso |
| `S3_SECRET_KEY` | `APP_S3_SECRET_KEY` | `""` | Chave secreta |
| `S3_URL_TTL` | `APP_S3_URL_TTL` | `900` | Validade do link assinado, em segundos |
| `MAX_UPLOAD_BYTES` | `APP_S3_MAX_UPLOAD_BYTES` | 25 MiB | Limite do `upload` |
| `MAX_IMAGE_BYTES` | `APP_S3_MAX_IMAGE_BYTES` | 2 MiB | Limite do `upload_image` |
| `MAX_IMAGE_PIXELS` | `APP_S3_MAX_IMAGE_PIXELS` | 4.000.000 | Largura x altura de qualquer imagem |
| `FILE_ENCRYPTION_KEY` | `APP_FILE_ENCRYPTION_KEY` | `""` | Chave mestra; vazia guarda os arquivos em claro |
| `ALLOWED_TYPES` | (só em Python) | PDF, PNG, JPEG, WebP | Política de upload, veja abaixo |

> **Use a região real do bucket.** Uma região errada costuma falhar como `NoSuchBucket`, e não como erro de credencial.

## Uso

```python
from tripaulx.storage import services as storage

key = storage.build_key("invoices", str(invoice.pk), name=uploaded.name)
# StoredFile(key, name, size, content_type, encrypted)
stored = storage.upload(uploaded, key)

# Para servir: em fluxo pela aplicação (vale para objetos cifrados e em claro) ...
response = StreamingHttpResponse(
    storage.download(stored.key), content_type=stored.content_type
)
# ... ou, para objetos guardados em claro, um link assinado.
url = storage.temporary_url(
    stored.key, download_name="Invoice.pdf", content_type="application/pdf"
)

storage.delete(stored.key)
```

| Função | O que faz |
|---|---|
| `build_key(*parts, name=)` | `tenants/<schema>/<parts>/<aleatório>-<nome limpo>` do schema ativo |
| `clean_name(name)` | Tira caminhos e acentos e mantém só `[A-Za-z0-9._-]` |
| `upload(file, key, content_type="", *, types=None, max_bytes=None)` | Valida e depois envia (cifrado quando há chave mestra). `types` restringe a política numa chamada e nunca a amplia |
| `upload_image(file, key, content_type="")` | O mesmo, limitado aos tipos `image/*` da política e a `MAX_IMAGE_BYTES` |
| `download(key)` | Iterador de pedaços em claro; decifra objetos cifrados e devolve os em claro como estão |
| `temporary_url(key, *, download_name="", content_type="")` | Link GET assinado, válido por `S3_URL_TTL` segundos |
| `delete(key)` | Apaga o objeto |
| `content_disposition(name, content_type)` | `inline` para `INLINE_TYPES`, `attachment` para o resto |

Toda função que recebe uma chave confere antes se ela pertence ao tenant ativo (`ensure_tenant_key`). Toda falha levanta `StorageError`, com mensagem traduzida que pode ser mostrada ao usuário.

Guarde o `content_type` real no seu próprio model. Com a cifra ligada, o objeto no bucket fica como `application/octet-stream`.

## Política de upload

`ALLOWED_TYPES` associa cada tipo MIME aceito às assinaturas que o conteúdo precisa ter. Cada assinatura é um par `(offset, bytes)`, e todos os pares precisam conferir. Offset `None` quer dizer "em qualquer ponto dos primeiros 1024 bytes". Isso cobre os PDFs que scanners e assinadores gravam com um preâmbulo.

```python
from tripaulx.storage.conf import DEFAULT_ALLOWED_TYPES

TRIPAULX = {
    # ...
    "ALLOWED_TYPES": {
        **DEFAULT_ALLOWED_TYPES,
        "image/gif": ((0, b"GIF8"),),
    },
}
```

O content type declarado vem do cliente e não prova nada, por isso a assinatura é sempre conferida. Imagens (`image/*`) também são abertas com o Pillow, que lê só o cabeçalho, e recusadas acima de `MAX_IMAGE_PIXELS`. Isso barra bombas de descompressão: um PNG de cor chapada com 12000x12000 pixels cabe em poucas centenas de KB.

Nunca libere SVG nem HTML. Os dois podem carregar scripts e, servidos inline no seu domínio, viram cross-site scripting.

## Criptografia

Alguns provedores compatíveis com S3 não têm criptografia real no servidor, e alguns aceitam chaves SSE-C e as ignoram em silêncio. Por isso o SDK cifra na aplicação:

1. Cada arquivo ganha uma chave aleatória de 32 bytes.
2. O conteúdo é cifrado com AES-256-GCM em pedaços de 1 MiB, cada um com seu próprio nonce.
3. O AAD de cada pedaço é o cabeçalho, o índice do pedaço e uma marca de último pedaço. Objetos reordenados, misturados ou truncados falham, em vez de devolver dados parciais.
4. A chave do arquivo é cifrada com a chave mestra (`FILE_ENCRYPTION_KEY`) e guardada no cabeçalho do objeto, que começa com a marca `TPX1\0`.

O download volta ao texto em claro para objetos sem a marca, como arquivos enviados antes de existir uma chave.

Isso protege contra credencial do bucket vazada, bucket exposto por engano e a equipe do próprio provedor. Não protege contra um servidor de aplicação comprometido, onde a chave mestra fica.

```bash
uv run python manage.py generate_file_key
```

> **Perder a chave mestra é perder todos os arquivos cifrados.** Guarde uma cópia fora do servidor, por exemplo num gerenciador de senhas. O `./start` gera uma chave local no `.env.local`. Em produção, defina `APP_FILE_ENCRYPTION_KEY` no app do CapRover.

## Teste de fumaça

```bash
uv run python manage.py check_bucket --schema acme [--keep]
```

O `check_bucket` roda um ciclo real contra o provedor: envia um objeto de teste, gera um link assinado, baixa por ele e apaga o objeto. Com a cifra ligada, prova também duas coisas: os bytes guardados são ilegíveis, e a aplicação consegue decifrá-los. Rode depois de configurar as credenciais. Um teste com mock não pega particularidades do provedor, como checksums recusados.

## Testes

Os testes nunca acessam a rede. Faça mock de `tripaulx.storage.client.get_client`, como a suíte do SDK faz. O `tests/conftest.py` do template desliga o storage e esvazia a chave de arquivos em todo teste, então o resultado nunca depende do `.env.local`.
