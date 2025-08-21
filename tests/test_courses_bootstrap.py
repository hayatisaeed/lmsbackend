def test_courses_health(client):
    resp = client.get("/api/v1/courses/health/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_courses_readiness(client):
    resp = client.get("/api/v1/courses/readiness/")
    assert resp.status_code == 200
    data = resp.json()
    assert "db" in data and "redis" in data and "storage" in data
