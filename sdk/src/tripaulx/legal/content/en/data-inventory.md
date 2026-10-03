# Data and systems inventory

> **Template.** This is the record of processing activities (LGPD art. 37, GDPR art. 30). Keep it in line with the data {{ product }} really processes and review it whenever a feature or supplier changes.

**Controller:** {{ company }} · **DPO:** {{ dpo_name }} ({{ dpo_email }}) · **Last review:** {{ effective_date }}

## 1. Processing activities

| ID | Activity | Data | Data subjects | Legal basis | Retention | Classification |
|---|---|---|---|---|---|---|
| P-01 | Accounts and sign-in | name, e-mail, password hash, second-factor settings | users | contract | while the account is active | Confidential |
| P-02 | Security logs | IP address, device, sign-in events | users | legitimate interest; legal obligation | limited period, then deleted | Confidential |
| P-03 | Workspace content | defined by each customer | customer's data subjects | customer's (we are processor) | customer's instructions | Restricted |
| P-04 | Billing | billing contact, tax identifiers, invoices | customers | legal obligation | as required by tax law | Confidential |
| P-05 | Support | messages, attachments | users | contract | 2 years after closing | Internal |
| P-06 | Transactional e-mails | e-mail address, message content | users | contract | supplier's log period | Internal |

## 2. Systems

| System | Purpose | Data | Location | Access |
|---|---|---|---|---|
| Application and API | {{ product }} | P-01 to P-06 | {{ data_location }} | engineering on call |
| PostgreSQL database | storage, one schema per workspace | P-01 to P-05 | {{ data_location }} | engineering on call |
| Object storage | files, encrypted at rest | P-03 | {{ data_location }} | the application only |
| Backups | recovery | copy of the above | {{ data_location }} | operations |
| E-mail provider | transactional e-mails | P-06 | supplier | the application only |

## 3. Data flows

1. The user signs in through the API; the request is authenticated with a token bound to the workspace.
2. Content is written to the workspace schema and, for files, to object storage.
3. Transactional e-mails leave through the e-mail provider.
4. Backups run on a schedule and are kept encrypted.

## 4. Suppliers (sub-processors)

| Supplier | Service | Data | Country | Agreement |
|---|---|---|---|---|
| (hosting) | servers and database | all | | DPA signed? |
| (object storage) | files | P-03 | | DPA signed? |
| (e-mail) | message delivery | P-06 | | DPA signed? |

## 5. Access review

| Group | Systems | Reviewed by | Frequency |
|---|---|---|---|
| Engineering on call | application, database, backups | {{ security_owner }} | quarterly |
| Workspace admins | their own workspace | each customer | quarterly |
