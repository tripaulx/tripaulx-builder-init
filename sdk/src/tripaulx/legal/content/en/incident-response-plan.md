# Incident response plan

> **Template.** Fill in the roles and contacts, rehearse the plan at least once a year and keep a printed or offline copy: during an incident the Service itself may be down.

**Owner:** {{ security_owner }} · **Last review:** {{ effective_date }}

## 1. Scope

A **security incident** is any confirmed or suspected event that compromises the confidentiality, integrity or availability of systems or data of {{ product }}: unauthorized access, leaks, loss of data, malware, account takeover, a supplier breach that reaches our data, or an outage caused by an attack.

## 2. Roles

| Role | Responsibility | Who |
|---|---|---|
| Incident lead | Coordinates the response and decides on escalation | {{ security_owner }} |
| Technical team | Investigates, contains and recovers | Engineering on call |
| DPO | Assesses the risk to people and leads notifications | {{ dpo_name }} |
| Communication | Messages to customers and the public | Management |
| Management | Approves notifications and relevant spending | Management |

Report channel for anyone, staff or not: **{{ security_email }}**.

## 3. Severity

| Severity | Criteria | First answer |
|---|---|---|
| Critical | Confirmed leak of personal data, cross-workspace access, ransomware | Immediately, any time |
| High | Suspected leak, compromised admin account, long outage | Within 2 hours |
| Medium | Contained malware, isolated compromised account | Next business day |
| Low | Blocked attempt, vulnerability without signs of exploitation | Regular backlog |

## 4. Phases

1. **Detect and record.** Open an entry in the incident register right away, with the time and who reported it. Do not delete anything.
2. **Triage.** The incident lead sets the severity and calls the needed roles.
3. **Contain.** Revoke sessions and keys, block accounts or addresses, isolate affected systems. Prefer reversible actions.
4. **Preserve evidence.** Keep logs, snapshots and copies with hashes and a chain of custody before changing systems.
5. **Investigate.** Establish the timeline, the entry point, the data and the people affected.
6. **Eradicate and recover.** Fix the cause, rotate secrets, restore from clean backups and monitor closely.
7. **Notify.** See section 5.
8. **Learn.** Within 15 days, hold a blameless review and turn the lessons into actions in the risk matrix and the backlog.

## 5. Notifications

- **Data protection authority** (in Brazil, the ANPD; in the EU, the lead supervisory authority) when the incident may bring relevant risk or harm to people: within the deadline set by the regulation in force (in Brazil, 3 business days; under the GDPR, 72 hours) counted from awareness.
- **Affected people**, in clear language: what happened, which data, the risks, the measures taken and what they can do.
- **Customers (controllers)**, when the incident reaches data we process on their behalf: without undue delay, so they can meet their own duties.

Each notification records: the date, the recipient, the content and who approved it.

## 6. Contacts

| Contact | Channel |
|---|---|
| Security reports | {{ security_email }} |
| DPO | {{ dpo_email }} |
| Hosting provider | (support channel) |
| E-mail provider | (support channel) |
| Legal counsel | (contact) |
