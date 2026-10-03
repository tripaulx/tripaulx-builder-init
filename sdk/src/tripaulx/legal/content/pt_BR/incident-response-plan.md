# Plano de resposta a incidentes

> **Modelo.** Preencha papéis e contatos, ensaie o plano pelo menos uma vez por ano e mantenha uma cópia impressa ou offline: durante um incidente o próprio Serviço pode estar fora do ar.

**Responsável:** {{ security_owner }} · **Última revisão:** {{ effective_date }}

## 1. Escopo

Um **incidente de segurança** é qualquer evento, confirmado ou suspeito, que comprometa a confidencialidade, a integridade ou a disponibilidade de sistemas ou dados de {{ product }}: acesso não autorizado, vazamento, perda de dados, malware, tomada de conta, violação em fornecedor que alcance nossos dados ou indisponibilidade causada por ataque.

## 2. Papéis

| Papel | Responsabilidade | Quem |
|---|---|---|
| Líder do incidente | Coordena a resposta e decide sobre escalonamento | {{ security_owner }} |
| Equipe técnica | Investiga, contém e recupera | Engenharia de plantão |
| Encarregado (DPO) | Avalia o risco às pessoas e conduz as comunicações | {{ dpo_name }} |
| Comunicação | Mensagens a clientes e ao público | Direção |
| Direção | Aprova comunicações e gastos relevantes | Direção |

Canal de comunicação para qualquer pessoa, da equipe ou não: **{{ security_email }}**.

## 3. Gravidade

| Gravidade | Critérios | Primeira resposta |
|---|---|---|
| Crítico | Vazamento confirmado de dados pessoais, acesso entre espaços, ransomware | Imediata, a qualquer hora |
| Alto | Suspeita de vazamento, conta de administrador comprometida, indisponibilidade longa | Em até 2 horas |
| Médio | Malware contido, conta comprometida isolada | No próximo dia útil |
| Baixo | Tentativa bloqueada, vulnerabilidade sem sinal de exploração | Backlog regular |

## 4. Fases

1. **Detectar e registrar.** Abra imediatamente uma entrada no registro de incidentes, com o horário e quem comunicou. Não apague nada.
2. **Triagem.** O líder do incidente define a gravidade e aciona os papéis necessários.
3. **Conter.** Revogue sessões e chaves, bloqueie contas ou endereços, isole sistemas afetados. Prefira ações reversíveis.
4. **Preservar evidências.** Guarde logs, snapshots e cópias com hash e cadeia de custódia antes de alterar sistemas.
5. **Investigar.** Estabeleça a linha do tempo, o ponto de entrada, os dados e as pessoas afetadas.
6. **Erradicar e recuperar.** Corrija a causa, troque segredos, restaure a partir de backups íntegros e monitore de perto.
7. **Comunicar.** Veja a seção 5.
8. **Aprender.** Em até 15 dias, faça uma revisão sem culpados e transforme as lições em ações na matriz de riscos e no backlog.

## 5. Comunicações

- **Autoridade de proteção de dados** (no Brasil, a ANPD; na UE, a autoridade de controle principal) quando o incidente puder acarretar risco ou dano relevante às pessoas: no prazo da regulamentação vigente (no Brasil, 3 dias úteis; pelo GDPR, 72 horas) contado da ciência.
- **Pessoas afetadas**, em linguagem clara: o que aconteceu, quais dados, os riscos, as medidas adotadas e o que elas podem fazer.
- **Clientes (controladores)**, quando o incidente alcançar dados que tratamos em nome deles: sem demora injustificada, para que cumpram seus próprios deveres.

Cada comunicação registra: data, destinatário, conteúdo e quem aprovou.

## 6. Contatos

| Contato | Canal |
|---|---|
| Comunicação de incidentes | {{ security_email }} |
| Encarregado | {{ dpo_email }} |
| Provedor de hospedagem | (canal de suporte) |
| Provedor de e-mail | (canal de suporte) |
| Assessoria jurídica | (contato) |
