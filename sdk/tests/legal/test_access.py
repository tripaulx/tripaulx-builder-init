"""E-mail domain rule: exact matches only."""

from tripaulx.legal.services import email_domain_allowed

DOMAINS = ("example.com",)


def test_exact_domain_is_allowed_case_insensitively():
    assert email_domain_allowed("jane@example.com", DOMAINS)
    assert email_domain_allowed("  Jane@EXAMPLE.com ", DOMAINS)


def test_look_alike_domains_are_refused():
    for email in (
        "x@example.com.attacker.test",
        "x@sub.example.com",
        "x@notexample.com",
        "x@example.co",
        "example.com",
        "@example.com",
        "x@attacker.test@example.co",
        "",
    ):
        assert not email_domain_allowed(email, DOMAINS), email


def test_no_domains_allows_nobody():
    assert not email_domain_allowed("jane@example.com", ())
    assert not email_domain_allowed("jane@example.com", ("",))
