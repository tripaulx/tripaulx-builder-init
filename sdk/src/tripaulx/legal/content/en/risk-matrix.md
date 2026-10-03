# Security and privacy risk matrix

> **Template.** Replace the example rows with the risks of {{ product }}, review the matrix at least every six months and after every relevant incident or architecture change.

**Owner:** {{ security_owner }} · **Last review:** {{ effective_date }}

## 1. Method

Each risk gets a **likelihood** and an **impact** from 1 to 5. The **score** is likelihood × impact.

| Score | Rating | Expected treatment |
|---:|---|---|
| 15–25 | Critical | Act immediately; management decides on any acceptance. |
| 10–14 | High | Treatment plan with owner and date within 30 days. |
| 5–9 | Medium | Treat in the regular roadmap; monitor. |
| 1–4 | Low | Accept and record; review at the next cycle. |

**Inherent** score: before controls. **Residual** score: with the current controls working.

## 2. Matrix

| ID | Risk | Likelihood | Impact | Inherent | Rating | Current controls | Residual | Owner |
|---|---|---:|---:|---:|---|---|---:|---|
| R-01 | Account takeover through stolen credentials | 4 | 5 | 20 | Critical | Mandatory second factor, passkeys, login throttling, trusted devices with expiry | 6 | Engineering |
| R-02 | One workspace reading another workspace's data | 2 | 5 | 10 | High | Schema per workspace, tokens bound to the schema, isolation tests | 5 | Engineering |
| R-03 | Leak of files from object storage | 3 | 5 | 15 | Critical | Private bucket, short-lived signed links, encryption at rest | 5 | Engineering |
| R-04 | Loss of data through failure or human error | 3 | 4 | 12 | High | Automated backups, restore tests, soft delete | 4 | Operations |
| R-05 | Secrets exposed in the repository or in logs | 3 | 4 | 12 | High | Secret scanning in CI, log redaction, environment variables | 4 | Engineering |
| R-06 | Vulnerable third-party dependency | 4 | 3 | 12 | High | Pinned versions, update routine, security advisories | 6 | Engineering |
| R-07 | Supplier processing data without adequate protection | 2 | 4 | 8 | Medium | Supplier review, data processing agreements | 4 | Legal |
| R-08 | Data subject request not answered on time | 2 | 3 | 6 | Medium | Request channel, owner and deadline in the register | 2 | DPO |
| R-09 | Former member keeps access after leaving | 3 | 3 | 9 | Medium | Member removal revokes sessions; quarterly access review | 3 | Workspace admins |
| R-10 | Service outage | 3 | 2 | 6 | Medium | Health checks, monitoring, documented redeploy | 3 | Operations |

## 3. Treatment plan

| ID | Action | Owner | Due date | Status |
|---|---|---|---|---|
| R-01 | Require passkeys or an authenticator app for every admin | Engineering | | Open |
| R-04 | Run and record a full restore test | Operations | | Open |
| R-06 | Automate dependency update pull requests | Engineering | | Open |

## 4. Acceptance

Risks accepted above **Medium** need a written decision by {{ company }} management, recorded here with the date and the reason.

| ID | Decision | Approved by | Date |
|---|---|---|---|
| | | | |
