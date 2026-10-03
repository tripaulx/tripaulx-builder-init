# Inventário de dados e sistemas

> **Modelo.** Este é o registro das operações de tratamento (LGPD art. 37, GDPR art. 30). Mantenha-o fiel aos dados que {{ product }} realmente trata e revise-o sempre que uma funcionalidade ou um fornecedor mudar.

**Controlador:** {{ company }} · **Encarregado:** {{ dpo_name }} ({{ dpo_email }}) · **Última revisão:** {{ effective_date }}

## 1. Operações de tratamento

| ID | Operação | Dados | Titulares | Base legal | Retenção | Classificação |
|---|---|---|---|---|---|---|
| P-01 | Contas e acesso | nome, e-mail, hash da senha, configuração do segundo fator | usuários | contrato | enquanto a conta estiver ativa | Confidencial |
| P-02 | Registros de segurança | endereço IP, dispositivo, eventos de acesso | usuários | legítimo interesse; obrigação legal | prazo limitado, depois excluídos | Confidencial |
| P-03 | Conteúdo dos espaços | definido por cada cliente | titulares do cliente | do cliente (somos operador) | instruções do cliente | Restrito |
| P-04 | Cobrança | contato de cobrança, identificadores fiscais, notas | clientes | obrigação legal | conforme a legislação fiscal | Confidencial |
| P-05 | Suporte | mensagens, anexos | usuários | contrato | 2 anos após o encerramento | Interno |
| P-06 | E-mails transacionais | endereço de e-mail, conteúdo da mensagem | usuários | contrato | prazo de log do fornecedor | Interno |

## 2. Sistemas

| Sistema | Finalidade | Dados | Local | Acesso |
|---|---|---|---|---|
| Aplicação e API | {{ product }} | P-01 a P-06 | {{ data_location }} | engenharia de plantão |
| Banco PostgreSQL | armazenamento, um schema por espaço | P-01 a P-05 | {{ data_location }} | engenharia de plantão |
| Armazenamento de arquivos | arquivos, criptografados em repouso | P-03 | {{ data_location }} | somente a aplicação |
| Backups | recuperação | cópia dos itens acima | {{ data_location }} | operações |
| Provedor de e-mail | e-mails transacionais | P-06 | fornecedor | somente a aplicação |

## 3. Fluxos de dados

1. O usuário entra pela API; a requisição é autenticada com um token preso ao espaço de trabalho.
2. O conteúdo é gravado no schema do espaço e, no caso de arquivos, no armazenamento de arquivos.
3. Os e-mails transacionais saem pelo provedor de e-mail.
4. Os backups rodam periodicamente e são guardados criptografados.

## 4. Fornecedores (suboperadores)

| Fornecedor | Serviço | Dados | País | Acordo |
|---|---|---|---|---|
| (hospedagem) | servidores e banco | todos | | DPA assinado? |
| (armazenamento) | arquivos | P-03 | | DPA assinado? |
| (e-mail) | envio de mensagens | P-06 | | DPA assinado? |

## 5. Revisão de acessos

| Grupo | Sistemas | Revisado por | Frequência |
|---|---|---|---|
| Engenharia de plantão | aplicação, banco, backups | {{ security_owner }} | trimestral |
| Administradores dos espaços | o próprio espaço | cada cliente | trimestral |
