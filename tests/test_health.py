import pytest


@pytest.mark.django_db
def test_healthz(client):
    resp = client.get("/api/v1/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readyz(client):
    resp = client.get("/api/v1/readyz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.django_db
def test_docs(client):
    resp = client.get("/api/v1/docs/")
    assert resp.status_code == 200
