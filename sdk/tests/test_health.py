from django.test import Client
import pytest


@pytest.mark.parametrize("path", ["/healthz", "/healthz/"])
def test_healthz_answers_on_any_host(path):
    response = Client(HTTP_HOST="10.0.0.7:8000").get(path)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readyz_checks_the_database():
    response = Client(HTTP_HOST="unknown.internal").get("/readyz/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_unknown_host_is_not_served():
    response = Client(HTTP_HOST="nobody.sdk.test").get("/admin/")
    assert response.status_code == 404
