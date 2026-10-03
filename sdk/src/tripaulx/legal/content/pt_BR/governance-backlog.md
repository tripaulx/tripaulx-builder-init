# Backlog de arquitetura e governança

> **Modelo.** Lista viva de melhorias de arquitetura, segurança e governança de dados. Vincule cada item ao risco que ele reduz e revise a lista a cada ciclo de planejamento.

**Responsável:** {{ security_owner }} · **Última revisão:** {{ effective_date }}

## 1. Princípios

- **Isolamento primeiro:** cada espaço de trabalho no seu próprio schema; nada cruza espaços sem uma regra explícita e testada.
- **Privilégio mínimo:** pessoas e serviços recebem só o acesso de que precisam, pelo tempo que precisarem.
- **Seguro por padrão:** novas funcionalidades já nascem com autenticação, validação, auditoria e testes.
- **Minimização de dados:** coletar e guardar apenas o que uma finalidade declarada exige.
- **Evidência:** decisões, revisões e incidentes deixam registro.

## 2. Backlog

| ID | Item | Risco | Prioridade | Responsável | Situação |
|---|---|---|---|---|---|
| B-01 | Exigir passkey ou app autenticador de todo administrador de espaço | R-01 | Alta | Engenharia | Aberto |
| B-02 | Testes automáticos que tentam ler dados entre espaços em todo endpoint | R-02 | Alta | Engenharia | Aberto |
| B-03 | Teste de restauração trimestral com resultado registrado | R-04 | Alta | Operações | Aberto |
| B-04 | Automação de atualização de dependências e revisão mensal de segurança | R-06 | Média | Engenharia | Aberto |
| B-05 | Acordos de tratamento de dados assinados com todos os fornecedores | R-07 | Média | Jurídico | Aberto |
| B-06 | Exportação, pelo próprio usuário, dos seus dados pessoais | R-08 | Média | Engenharia | Aberto |
| B-07 | Alertas para padrões incomuns de acesso | R-01 | Média | Engenharia | Aberto |
| B-08 | Rotinas de retenção que excluem logs vencidos e espaços encerrados | R-05 | Baixa | Engenharia | Aberto |

## 3. Registro de decisões

| Data | Decisão | Motivo | Quem decidiu |
|---|---|---|---|
| | | | |

## 4. Cadência de revisão

- **Mensal:** situação dos itens abertos.
- **A cada seis meses:** este backlog, a matriz de riscos e o inventário de dados, em conjunto.
- **Após cada incidente:** incluir as ações da revisão do incidente.
