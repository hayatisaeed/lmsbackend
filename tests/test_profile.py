import pytest

from apps.users.models import (
    City,
    EducationalLevel,
    EducationalGrade,
    IdentityInfo,
    Olympiad,
    OTPCode,
    Province,
    StudyBranch,
    User,
)
from apps.users.utils import generate_access_token


@pytest.fixture
def auth_client(db, client):
    user = User.objects.create(phone="+1000000000", display_name="Test")
    token, _ = generate_access_token(user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client, user


def test_identity_encryption_and_rate_limit(auth_client, monkeypatch):
    client, user = auth_client

    def fake_verify(nid, dob):
        return {"first_name": "A", "last_name": "B", "verified": True}

    monkeypatch.setattr(
        "apps.users.serializers.verify_identity_with_provider", fake_verify
    )
    resp = client.post(
        "/api/v1/profile/identity",
        {"national_id": "123456", "date_of_birth": "2010-01-01"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    info = IdentityInfo.objects.get(user=user)
    assert info.national_id != "123456"
    for _ in range(4):
        client.post(
            "/api/v1/profile/identity",
            {"national_id": "123456", "date_of_birth": "2010-01-01"},
            content_type="application/json",
        )
    resp = client.post(
        "/api/v1/profile/identity",
        {"national_id": "123456", "date_of_birth": "2010-01-01"},
        content_type="application/json",
    )
    assert resp.status_code == 429


def test_education_and_location_and_parent_flow(auth_client, monkeypatch):
    client, user = auth_client

    def fake_verify(nid, dob):
        return {"verified": True, "first_name": "A", "last_name": "B"}

    monkeypatch.setattr(
        "apps.users.serializers.verify_identity_with_provider", fake_verify
    )
    client.post(
        "/api/v1/profile/identity",
        {"national_id": "123456", "date_of_birth": "2010-01-01"},
        content_type="application/json",
    )
    level = EducationalLevel.objects.create(
        name="HighSchool", min_grade=10, max_grade=12, is_high_school=True
    )
    grade_obj = EducationalGrade.objects.create(name="11", level=level)
    branch = StudyBranch.objects.create(level=level, name="Math")
    olymp = Olympiad.objects.create(name="O1", olympiad_degree=1, published=True)
    resp = client.post(
        "/api/v1/profile/education",
        {
            "level": level.id,
            "grade": grade_obj.id,
            "study_branch": branch.id,
            "olympiad_ids": [olymp.id],
        },
        content_type="application/json",
    )
    assert resp.status_code == 200
    prov = Province.objects.create(name="Tehran", slug="tehran")
    City.objects.create(name="Tehran", slug="tehran", province=prov)
    resp = client.post(
        "/api/v1/profile/location",
        {"province": "Tehran", "city": "Tehran"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    resp = client.post(
        "/api/v1/profile/parent",
        {"phone": "+12223334444", "relation": "father"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    code = OTPCode.objects.get(phone="+12223334444", purpose="parent").code
    resp = client.post(
        "/api/v1/profile/parent/verify", {"code": code}, content_type="application/json"
    )
    assert resp.status_code == 200
    resp = client.get("/api/v1/profile/completion")
    assert resp.json()["percent_complete"] == 100
    profile = client.get("/api/v1/profile").json()
    assert profile["identity"]["verified"] is True
