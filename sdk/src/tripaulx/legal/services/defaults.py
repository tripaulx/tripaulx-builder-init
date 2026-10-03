"""Documents the SDK ships templates for (``content/<language>/``)."""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from .document import PUBLIC, LegalDocument

GOVERNANCE = _("Governance")
RECORDS = _("Records")
INVENTORY = _("Inventory")
ARCHITECTURE = _("Architecture")
POLICIES = _("Policies")

DEFAULT_DOCUMENTS: tuple[LegalDocument, ...] = (
    LegalDocument(
        "terms-of-use",
        _("Terms of use"),
        _("Rules for using the service, accounts and responsibilities."),
        "terms-of-use.md",
        POLICIES,
        PUBLIC,
    ),
    LegalDocument(
        "privacy-policy",
        _("Privacy policy"),
        _("Which personal data is processed, why, for how long and your rights."),
        "privacy-policy.md",
        POLICIES,
        PUBLIC,
    ),
    LegalDocument(
        "risk-matrix",
        _("Security and privacy risk matrix"),
        _("Risks, controls, owners and treatment actions."),
        "risk-matrix.md",
        GOVERNANCE,
    ),
    LegalDocument(
        "incident-response-plan",
        _("Incident response plan"),
        _("How to detect, contain, investigate and report incidents."),
        "incident-response-plan.md",
        GOVERNANCE,
    ),
    LegalDocument(
        "incident-register",
        _("Incident register"),
        _("Policy and minimum format for recording every occurrence."),
        "incident-register.md",
        RECORDS,
    ),
    LegalDocument(
        "incident-record-template",
        _("Incident record template"),
        _("Form to copy for each new incident record."),
        "incident-record-template.md",
        RECORDS,
    ),
    LegalDocument(
        "data-inventory",
        _("Data and systems inventory"),
        _("Data processed, systems, flows, access, retention and suppliers."),
        "data-inventory.md",
        INVENTORY,
    ),
    LegalDocument(
        "governance-backlog",
        _("Architecture and governance backlog"),
        _("Architecture, security and governance improvements to schedule."),
        "governance-backlog.md",
        ARCHITECTURE,
    ),
)
