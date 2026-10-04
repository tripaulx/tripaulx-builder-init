# Contas, cadastro e e-mail

`tripaulx.accounts` cobre o cadastro de workspace, o login com segundo fator
obrigatório, o aplicativo autenticador (TOTP), passkeys, códigos de
recuperação, dispositivos confiáveis, redefinição e troca de senha, membros
do workspace e convites. `tripaulx.mail` envia os e-mails pelo Mailgun.

Versão em inglês (a fonte): [../accounts.md](../accounts.md).

## Ligação

O template do projeto já faz tudo isto.

```python
# config/settings/base_parts/rest.py
from tripaulx.settings.rest import rest_framework, simple_jwt, spectacular

REST_FRAMEWORK = rest_framework()  # TenantJWTAuthentication, throttles
SIMPLE_JWT = simple_jwt(get_env("JWT_SIGNING_KEY", ""))  # vazio: SECRET_KEY
SPECTACULAR_SETTINGS = spectacular("Acme API")  # docs só para admins
```

```python
# config/urls.py (workspaces)
(path("api/auth/", include("tripaulx.accounts.api.urls")),)
(path("api/workspace/", include("tripaulx.accounts.api.urls_workspace")),)

# config/urls_public.py (domínio raiz)
(path("api/auth/", include("tripaulx.accounts.api.urls_public")),)  # cadastro
(path("api/auth/", include("tripaulx.accounts.api.urls")),)
```

`tripaulx.settings.apps` instala `rest_framework`, `drf_spectacular`,
`corsheaders`, `rest_framework_simplejwt.token_blacklist` (em todo schema,
junto dos usuários) e `tripaulx.mail` (só no schema public).

## Fluxos

### Cadastro (schema public)

1. `POST /api/auth/signup/` com
   `{email, full_name, password, password_confirm, workspace_name, slug?}`.
   O nome completo vira `first_name` (primeira palavra) e `last_name` (o resto).
   Sem `slug`, ele sai do nome (`Acme Ltda` → `acme_ltda`).
2. O SDK valida o slug (palavras reservadas, formato, disponibilidade) e a
   senha, e cria o `Workspace`, o schema (todas as migrations de tenant) e o
   `Domain` `<slug>.<BASE_DOMAIN>` numa única transação.
3. Dentro do schema novo, cria o owner (`role=owner`, `email_verified=False`)
   e envia o código de confirmação por e-mail.
4. A resposta é `201` com `workspace_slug`, `workspace_domain`,
   `workspace_url`, `email` e `email_verification_required`.
5. Signals: `tripaulx.tenants.signals.workspace_created` (após o commit) e
   `tripaulx.accounts.signals.user_signed_up`.

Criar um schema leva cerca de um segundo com as apps do SDK; o tempo cresce
com as migrations de tenant do projeto. O cadastro é protegido por
`SIGNUP_ENABLED` e pelo throttle `auth_register`.

### Confirmação de e-mail

`POST /api/auth/email/verify/` com `{email, code}` marca o endereço como
confirmado e devolve os tokens (o código prova o acesso à caixa).
`POST /api/auth/email/resend/` envia um código novo; a resposta é sempre a
mesma, exista a conta ou não.

### Login: o segundo fator é sempre exigido

1. `POST /api/auth/login/` com `{email, password, device_token?}`.
   - Credenciais erradas: `401`.
   - Conta "somente passkey" (senha certa): `403` com `passkey_required`.
   - E-mail não confirmado: `403` com `email_verification_required` (um
     código é enviado).
   - Um `device_token` válido (dispositivo confiável) pula o segundo fator e
     devolve os tokens.
   - Senão: `{mfa_required, ticket, mfa_method}`. `mfa_method` é `totp` quando
     o aplicativo está confirmado (nenhum e-mail é enviado), senão `email`
     (com `masked_email`).
2. `POST /api/auth/login/verify/` com `{ticket, code, trust_device?,
   device_label?}`. O campo `code` aceita o código do aplicativo, o do e-mail
   ou um código de recuperação. Com `trust_device`, a resposta traz
   `device_token` e `device_token_max_age`.
3. `POST /api/auth/login/resend/` com `{ticket}` envia um novo código por
   e-mail (nunca para quem usa o aplicativo; mesma resposta em todo caso).

O ticket é assinado, expira em `LOGIN_TICKET_TTL_SECONDS` e é preso ao
schema. Contas privilegiadas (owner, admin, staff) sem aplicativo nem passkey
recebem `mfa_setup_required: true` no usuário, para o cliente pedir um fator
forte.

### Tokens presos ao workspace

Todo JWT carrega o claim `schema`. A `TenantJWTAuthentication` recusa token
emitido em outro schema (os ids de usuário se repetem entre schemas), e o
refresh e o logout também (`TenantRefreshToken`). O access dura 30 minutos e
o refresh 12 horas, com rotação e blacklist. O refresh tem throttle próprio
(`auth_refresh`).

### Aplicativo autenticador (TOTP)

RFC 6238 escrito à mão (conferido com os vetores da RFC), 6 dígitos,
intervalos de 30 segundos, um intervalo de tolerância e anti-replay. O
segredo fica cifrado.

- `POST /api/auth/totp/setup/` devolve `secret`, `otpauth_uri` e `qr_svg`
  (só aqui); `DELETE` cancela uma configuração pendente.
- `POST /api/auth/totp/confirm/` com o primeiro código ativa e devolve 9
  códigos de recuperação, exibidos uma única vez.
- `POST /api/auth/totp/disable/` exige um código do aplicativo ou de
  recuperação.
- `GET /api/auth/totp/` devolve o estado.

### Códigos de recuperação

Formato `XXXXX-XXXXX` sem caracteres parecidos, guardados como hash, de uso
único. Uma lista nova invalida a anterior. `GET /api/auth/mfa/recovery-codes/`
conta os restantes e `POST` gera uma lista nova (`quantity` de 1 a 20). Quem
opera o servidor pode rodar
`manage.py generate_recovery_codes --schema acme --user jane@example.com`.

### Passkeys (WebAuthn)

- Cadastrar (logado): `POST passkey/register/begin/` e depois
  `POST passkey/register/complete/` com `{credential, name}`.
- Login: `POST passkey/login/begin/` com `email` opcional e depois
  `POST passkey/login/complete/` com `{ticket, credential}`. Aqui o e-mail
  também precisa estar confirmado.
- Gerenciar: `GET passkey/credentials/`, `PATCH passkey/credentials/<id>/`
  (renomear), `DELETE passkey/credentials/<id>/`.
- Somente passkey: `POST passkey/password-login/` com `{disabled: true}`.
  Exige uma passkey; só vale enquanto houver uma; a última passkey não pode
  ser removida com o login por senha desligado.

O RP ID é o host da requisição (o subdomínio de cada workspace), a menos que
`WEBAUTHN_RP_ID` fixe um domínio-pai. Os desafios ficam no cache do Django:
**em produção com mais de um worker é obrigatório um cache compartilhado
(Redis, `REDIS_URL`)**, senão o "complete" pode cair num worker que nunca viu
o desafio.

### Dispositivos confiáveis

`GET /api/auth/devices/` lista os ativos (nunca o token);
`DELETE /api/auth/devices/<id>/` revoga um.

### Senhas

- `POST /api/auth/password/reset/` com `{email}` envia um código (silencioso
  para endereços desconhecidos).
- `POST /api/auth/password/reset/confirm/` com
  `{email, code, password, password_confirm}`. A
  senha é validada antes de o código ser consumido; toda falha tem a mesma
  mensagem.
- `POST /api/auth/password/change/` com
  `{current_password, new_password, new_password_confirm}` (logado) devolve um
  par de tokens novo.

Redefinir e trocar a senha revogam todos os dispositivos confiáveis e fazem
blacklist de todos os refresh tokens do usuário.

### Regras de senha

Todo lugar que define uma senha exige a confirmação igual e roda os
`AUTH_PASSWORD_VALIDATORS` do projeto *contra a pessoa*: e-mail, nome e
sobrenome. Assim o `UserAttributeSimilarityValidator` recusa senhas parecidas
com os dados da própria pessoa, inclusive no cadastro, antes de o usuário
existir. Vale para cadastro, reset e troca de senha, aceite de convite e
`create_workspace_admin`.

- Confirmação diferente responde `400` com `field: "password_confirm"`; regra
  violada responde `field: "password"` com as mensagens (traduzidas) dos
  validadores.
- `GET /api/auth/password/rules/` (anônimo) devolve `{"rules": [...]}`, os
  textos de ajuda dos validadores no idioma da requisição, para os formulários
  mostrarem antes.

### O primeiro administrador de um workspace

`manage.py create_workspace_admin --schema <slug>` pede e-mail, nome completo e
a senha duas vezes. A senha fica oculta, as regras aparecem antes e a pergunta
se repete quando uma regra falha. O comando cria um owner com e-mail
confirmado e acesso ao admin do Django.
- Opções: `--email`, `--full-name`, `--role owner|admin|member`, `--no-superuser`.
- `--password-stdin` lê a senha do stdin, para scripts.
- `--if-none` não faz nada se o workspace já tiver um owner.

Nos projetos gerados, o `./start setup` roda o comando com `--if-none` para o
primeiro workspace quando está num terminal (onboarding). O `./start admin`
roda a qualquer momento.

### Membros e convites (owners e admins)

Permissão: `tripaulx.accounts.api.permissions.IsWorkspaceAdmin`.

- `GET /api/workspace/members/` e `GET|PATCH|DELETE
  /api/workspace/members/<id>/` (PATCH `{role}`; DELETE desativa e encerra as
  sessões).
- `GET|POST /api/workspace/invitations/` (`{email, role}`) e
  `DELETE /api/workspace/invitations/<id>/` revoga.
- `POST /api/auth/invitations/accept/` (anônimo) com `{token, password,
  password_confirm, full_name?}` (ou `first_name?`/`last_name?`) cria o usuário com e-mail confirmado e o papel do
  convite, e devolve os tokens.

Regras: só um owner altera outro owner ou concede o papel de owner; o
workspace sempre mantém um owner ativo. O link do convite é
`INVITATION_ACCEPT_URL` formatado com a origem da requisição e o token.

## Resumo dos endpoints

| Método | Caminho (`/api/auth/` salvo indicação) | Autenticação |
|---|---|---|
| POST | `signup/` (schema public) | anônimo |
| POST | `email/verify/`, `email/resend/` | anônimo |
| POST | `login/`, `login/verify/`, `login/resend/` | anônimo |
| POST | `token/refresh/` | refresh token |
| POST | `logout/` | JWT |
| GET | `me/` | JWT |
| POST | `password/reset/`, `password/reset/confirm/` | anônimo |
| POST | `password/change/` | JWT |
| GET | `password/rules/` | anônimo |
| GET, POST | `mfa/recovery-codes/` | JWT |
| GET / POST, DELETE / POST / POST | `totp/`, `totp/setup/`, `totp/confirm/`, `totp/disable/` | JWT |
| GET / DELETE | `devices/`, `devices/<id>/` | JWT |
| POST | `passkey/register/begin/`, `passkey/register/complete/` | JWT |
| GET / PATCH, DELETE | `passkey/credentials/`, `passkey/credentials/<id>/` | JWT |
| POST | `passkey/password-login/` | JWT |
| POST | `passkey/login/begin/`, `passkey/login/complete/` | anônimo |
| POST | `invitations/accept/` | anônimo |
| GET / GET, PATCH, DELETE | `/api/workspace/members/`, `.../<id>/` | owner/admin |
| GET, POST / DELETE | `/api/workspace/invitations/`, `.../<id>/` | owner/admin |

## Configurações (`TRIPAULX`)

| Chave | Padrão | Significado |
|---|---|---|
| `APP_NAME` | `"App"` | Marca nos e-mails, issuer do TOTP e nome do RP das passkeys |
| `FIELD_ENCRYPTION_KEY` | `""` | Chave Fernet; vazia deriva uma do `SECRET_KEY` (só em dev) |
| `EMAIL_LOGO_URL` | `""` | Logo no topo dos e-mails HTML |
| `OTP_LENGTH` | `6` | Dígitos dos códigos por e-mail |
| `OTP_TTL_SECONDS` | `600` | Validade dos códigos por e-mail |
| `OTP_MAX_ATTEMPTS` | `5` | Erros antes de o código morrer |
| `OTP_RESEND_COOLDOWN` | `60` | Segundos entre dois códigos da mesma finalidade |
| `LOGIN_TICKET_TTL_SECONDS` | `600` | Validade do ticket de login |
| `TRUSTED_DEVICE_MAX_AGE` | 30 dias | Validade de um dispositivo confiável |
| `RECOVERY_CODES_QUANTITY` | `9` | Tamanho padrão da lista de recuperação |
| `TOTP_ISSUER` | `""` | Issuer no aplicativo; vazio usa `APP_NAME` |
| `WEBAUTHN_RP_ID` | `""` | Vazio usa o host da requisição |
| `WEBAUTHN_RP_NAME` | `""` | Vazio usa `APP_NAME` |
| `WEBAUTHN_ORIGINS` | `()` | Origens extras aceitas |
| `WEBAUTHN_CHALLENGE_TTL` | `300` | Segundos que um desafio fica no cache |
| `SIGNUP_ENABLED` | `True` | Liga/desliga o cadastro público |
| `INVITATION_TTL_SECONDS` | 7 dias | Validade de um convite |
| `INVITATION_ACCEPT_URL` | `"{origin}/accept-invitation?token={token}"` | Link no e-mail de convite |

Escopos de throttle (`rest_framework()`): `anon` 100/hora, `user` 1000/hora,
`auth_login` 10/min, `auth_register` 5/min, `auth_otp` 10/min e
`auth_refresh` 60/min. Para trocar um:
`rest_framework(DEFAULT_THROTTLE_RATES={"anon": "50/hour"})`.

## E-mail

Os templates ficam em `templates/tripaulx/mail/`: `base.html`, `code_base.*`,
`email_verify.*`, `login_2fa.*`, `password_reset.*` e `invite.*` (`.html` e
`.txt`). O projeto sobrescreve qualquer um criando o mesmo caminho na própria
pasta `templates/`. O contexto traz `app_name` e `logo_url`.

O backend do Mailgun lê a configuração do singleton `MailgunConfig` (admin do
schema public; a API key é cifrada com `core.crypto`). Enquanto ele não está
ligado, com chave e domínio, as mensagens vão para o backend de fallback.

```python
MAILERS = {
    "default": {
        "BACKEND": "tripaulx.mail.backends.MailgunEmailBackend",
        "OPTIONS": {
            "fallback_backend": "django.core.mail.backends.smtp.EmailBackend",
            "fallback_options": {"host": "smtp.example.com", "port": 587},
            "timeout": 10,
        },
    },
}
```

Cada chave de `OPTIONS` é um argumento nomeado do backend; o Django recusa as
desconhecidas.

## Campos cifrados

`tripaulx.core.crypto.encrypt()` / `decrypt()` usam Fernet com a
`FIELD_ENCRYPTION_KEY`. `decrypt()` registra o erro no log e devolve `""`
quando a chave está errada. O `prod.py` do template chama
`validate_field_key()`, então a produção não sobe sem uma chave válida; o
`./start` gera uma no `.env.local`.

## Testes

`tripaulx.core.testing.TenantAPITestCase` oferece `api_client(user=None)`
(cliente DRF no domínio do tenant com JWT preso ao schema) e
`anon_api_client()`.
