# Architecture and governance backlog

> **Template.** A living list of improvements to architecture, security and data governance. Link each item to the risk it reduces and review the list at every planning cycle.

**Owner:** {{ security_owner }} · **Last review:** {{ effective_date }}

## 1. Principles

- **Isolation first:** every workspace in its own schema; nothing crosses workspaces without an explicit, tested rule.
- **Least privilege:** people and services get only the access they need, for as long as they need it.
- **Secure by default:** new features start with authentication, validation, audit and tests.
- **Data minimization:** collect and keep only what a stated purpose needs.
- **Evidence:** decisions, reviews and incidents leave a record.

## 2. Backlog

| ID | Item | Risk | Priority | Owner | Status |
|---|---|---|---|---|---|
| B-01 | Require passkeys or an authenticator app for every workspace admin | R-01 | High | Engineering | Open |
| B-02 | Automated tests that try to read across workspaces on every endpoint | R-02 | High | Engineering | Open |
| B-03 | Quarterly restore test with recorded result | R-04 | High | Operations | Open |
| B-04 | Dependency update automation and a monthly security review | R-06 | Medium | Engineering | Open |
| B-05 | Data processing agreements signed with every supplier | R-07 | Medium | Legal | Open |
| B-06 | Self-service export of a user's personal data | R-08 | Medium | Engineering | Open |
| B-07 | Alerting on unusual sign-in patterns | R-01 | Medium | Engineering | Open |
| B-08 | Retention jobs that delete expired logs and closed workspaces | R-05 | Low | Engineering | Open |

## 3. Decisions log

| Date | Decision | Reason | Who decided |
|---|---|---|---|
| | | | |

## 4. Review cadence

- **Monthly:** status of open items.
- **Every six months:** this backlog, the risk matrix and the data inventory together.
- **After every incident:** add the actions from its review.
