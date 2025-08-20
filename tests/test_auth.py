from http.cookies import SimpleCookie

import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.users.models import OTPCode

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _override_cache(settings):
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


PHONE = "+12345678901"


def _get_refresh_cookie(resp) -> SimpleCookie:
    return resp.cookies[settings.REFRESH_COOKIE_NAME]


def test_request_otp_and_cooldown(client):
    resp = client.post("/api/v1/auth/request-otp", {"phone": PHONE}, format="json")
    assert resp.status_code == 200
    assert resp.json()["is_new_user"] is True
    # second call within cooldown
    resp2 = client.post("/api/v1/auth/request-otp", {"phone": PHONE}, format="json")
    assert resp2.status_code == 429


def test_verify_requires_display_name(client):
    client.post("/api/v1/auth/request-otp", {"phone": PHONE}, format="json")
    code = OTPCode.objects.get(phone=PHONE).code
    resp = client.post(
        "/api/v1/auth/verify-otp",
        {"phone": PHONE, "code": code},
        format="json",
    )
    assert resp.status_code == 400


def test_full_auth_flow(client):
    client.post("/api/v1/auth/request-otp", {"phone": PHONE}, format="json")
    code = OTPCode.objects.get(phone=PHONE).code
    verify = client.post(
        "/api/v1/auth/verify-otp",
        {"phone": PHONE, "code": code, "display_name": "John"},
        format="json",
    )
    assert verify.status_code == 200
    access = verify.json()["access_token"]
    cookie = _get_refresh_cookie(verify)
    assert cookie["httponly"]
    assert cookie["secure"]
    assert cookie["samesite"].lower() == settings.COOKIE_SAMESITE.lower()
    assert cookie["path"] == "/"

    # refresh rotation
    client.cookies.load({settings.REFRESH_COOKIE_NAME: cookie.value})
    r1 = client.post("/api/v1/auth/refresh")
    assert r1.status_code == 200
    new_cookie = _get_refresh_cookie(r1)
    # reuse old token
    client.cookies.load({settings.REFRESH_COOKIE_NAME: cookie.value})
    reuse = client.post("/api/v1/auth/refresh")
    assert reuse.status_code == 419
    # new token should now be revoked
    client.cookies.load({settings.REFRESH_COOKIE_NAME: new_cookie.value})
    r2 = client.post("/api/v1/auth/refresh")
    assert r2.status_code == 409

    # logout clears cookie
    client.cookies.load({settings.REFRESH_COOKIE_NAME: new_cookie.value})
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    cookie = logout.cookies.get(settings.REFRESH_COOKIE_NAME)
    assert cookie is not None and cookie.value == ""

    # session introspection
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    sess = client.get("/api/v1/auth/session")
    assert sess.status_code == 200
    assert sess.json()["user"]["phone"] == PHONE
    assert sess.json()["is_new_user"] is True
    # second call flips flag
    sess2 = client.get("/api/v1/auth/session")
    assert sess2.json()["is_new_user"] is False
