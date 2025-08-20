import pytest

from apps.users.models import City, EducationalLevel, Olympiad, Province, StudyBranch


@pytest.mark.django_db
def test_educational_levels_and_branches_and_olympiads(client):
    level1 = EducationalLevel.objects.create(
        name="Elementary", min_grade=1, max_grade=6, is_high_school=False
    )
    level2 = EducationalLevel.objects.create(
        name="High School", min_grade=10, max_grade=12, is_high_school=True
    )
    StudyBranch.objects.create(level=level2, name="Math", is_active=True)
    StudyBranch.objects.create(level=level2, name="Physics", is_active=False)
    StudyBranch.objects.create(level=level1, name="Other", is_active=True)

    resp = client.get("/api/v1/educational-levels")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get("/api/v1/study-branches", {"level": level2.id, "active": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1 and data[0]["name"] == "Math"

    resp = client.get("/api/v1/study-branches", {"level": level1.id})
    assert resp.status_code == 404

    Olympiad.objects.create(name="O1", olympiad_degree=1, published=True)
    Olympiad.objects.create(name="O2", olympiad_degree=2, published=False)
    resp = client.get("/api/v1/olympiads")
    assert len(resp.json()) == 1
    resp = client.get("/api/v1/olympiads", {"published": "false"})
    assert len(resp.json()) == 1 and resp.json()[0]["name"] == "O2"


@pytest.mark.django_db
def test_locations_modes(client):
    prov1 = Province.objects.create(name="Tehran", slug="tehran")
    city1 = City.objects.create(name="Tehran", slug="tehran-city", province=prov1)
    prov2 = Province.objects.create(name="Isfahan", slug="isfahan")
    City.objects.create(name="Isfahan", slug="isfahan-city", province=prov2)

    resp = client.get("/api/v1/locations")
    assert resp.status_code == 200
    data = {p["slug"]: p for p in resp.json()}
    assert data["tehran"]["cities_count"] == 1

    resp = client.get("/api/v1/locations", {"state": "tehran"})
    assert resp.status_code == 200
    assert resp.json() == [{"id": city1.id, "name": city1.name, "slug": city1.slug}]

    resp = client.get("/api/v1/locations", {"all": "true"})
    assert resp.status_code == 200
    all_data = {p["slug"]: p for p in resp.json()}
    assert all_data["tehran"]["cities"][0]["id"] == city1.id

    resp = client.get("/api/v1/locations", {"q": "isfa"})
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names == ["Isfahan"]
