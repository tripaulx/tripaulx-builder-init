# Matriz de riscos de segurança e privacidade

> **Modelo.** Substitua as linhas de exemplo pelos riscos de {{ product }}, revise a matriz pelo menos a cada seis meses e após todo incidente ou mudança de arquitetura relevante.

**Responsável:** {{ security_owner }} · **Última revisão:** {{ effective_date }}

## 1. Método

Cada risco recebe **probabilidade** e **impacto** de 1 a 5. A **pontuação** é probabilidade × impacto.

| Pontuação | Classificação | Tratamento esperado |
|---:|---|---|
| 15–25 | Crítico | Agir imediatamente; a direção decide sobre qualquer aceitação. |
| 10–14 | Alto | Plano de tratamento com responsável e prazo em até 30 dias. |
| 5–9 | Médio | Tratar no roadmap regular; monitorar. |
| 1–4 | Baixo | Aceitar e registrar; revisar no próximo ciclo. |

Pontuação **inerente**: antes dos controles. Pontuação **residual**: com os controles atuais funcionando.

## 2. Matriz

| ID | Risco | Probabilidade | Impacto | Inerente | Classificação | Controles atuais | Residual | Responsável |
|---|---|---:|---:|---:|---|---|---:|---|
| R-01 | Tomada de conta por credenciais roubadas | 4 | 5 | 20 | Crítico | Segundo fator obrigatório, passkeys, limite de tentativas, dispositivos confiáveis com validade | 6 | Engenharia |
| R-02 | Um espaço de trabalho ler dados de outro | 2 | 5 | 10 | Alto | Schema por espaço, tokens presos ao schema, testes de isolamento | 5 | Engenharia |
| R-03 | Vazamento de arquivos do armazenamento | 3 | 5 | 15 | Crítico | Bucket privado, links assinados de curta duração, criptografia em repouso | 5 | Engenharia |
| R-04 | Perda de dados por falha ou erro humano | 3 | 4 | 12 | Alto | Backups automáticos, testes de restauração, exclusão lógica | 4 | Operações |
| R-05 | Segredos expostos no repositório ou em logs | 3 | 4 | 12 | Alto | Varredura de segredos na CI, redação de logs, variáveis de ambiente | 4 | Engenharia |
| R-06 | Dependência de terceiros vulnerável | 4 | 3 | 12 | Alto | Versões fixadas, rotina de atualização, alertas de segurança | 6 | Engenharia |
| R-07 | Fornecedor tratando dados sem proteção adequada | 2 | 4 | 8 | Médio | Avaliação de fornecedores, acordos de tratamento de dados | 4 | Jurídico |
| R-08 | Pedido de titular não atendido no prazo | 2 | 3 | 6 | Médio | Canal de pedidos, responsável e prazo no registro | 2 | Encarregado |
| R-09 | Ex-membro mantém acesso após sair | 3 | 3 | 9 | Médio | Remoção do membro revoga sessões; revisão trimestral de acessos | 3 | Administradores dos espaços |
| R-10 | Indisponibilidade do serviço | 3 | 2 | 6 | Médio | Health checks, monitoramento, redeploy documentado | 3 | Operações |

## 3. Plano de tratamento

| ID | Ação | Responsável | Prazo | Situação |
|---|---|---|---|---|
| R-01 | Exigir passkey ou app autenticador de todo administrador | Engenharia | | Aberta |
| R-04 | Executar e registrar um teste completo de restauração | Operações | | Aberta |
| R-06 | Automatizar pull requests de atualização de dependências | Engenharia | | Aberta |

## 4. Aceitação

Riscos aceitos acima de **Médio** exigem decisão escrita da direção de {{ company }}, registrada aqui com data e motivo.

| ID | Decisão | Aprovado por | Data |
|---|---|---|---|
| | | | |
