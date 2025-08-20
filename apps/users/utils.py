import random
import uuid
from datetime import timedelta
from typing import Tuple

import jwt
import requests
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone

from .models import OTPCode, RefreshSession, User


def generate_otp(phone: str, ip: str | None = None, purpose: str = "login") -> OTPCode:
    code = "".join(str(random.randint(0, 9)) for _ in range(settings.OTP_LENGTH))
    otp = OTPCode.objects.create(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SEC),
        ip=ip,
    )
    return otp


def generate_access_token(user: User) -> Tuple[str, int]:
    now = timezone.now()
    exp = now + timedelta(seconds=settings.JWT_ACCESS_TTL_SEC)
    payload = {
        "sub": str(user.id),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALG)
    return token, settings.JWT_ACCESS_TTL_SEC


def generate_refresh_session(
    user: User, rotated_from: RefreshSession | None = None
) -> Tuple[RefreshSession, str]:
    session = RefreshSession.objects.create(
        user=user,
        jti=uuid.uuid4(),
        expires_at=timezone.now() + timedelta(seconds=settings.JWT_REFRESH_TTL_SEC),
        rotated_from=rotated_from,
    )
    token_payload = {
        "sub": str(user.id),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(timezone.now().timestamp()),
        "exp": int(
            (
                timezone.now() + timedelta(seconds=settings.JWT_REFRESH_TTL_SEC)
            ).timestamp()
        ),
        "jti": str(session.jti),
    }
    token = jwt.encode(
        token_payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALG
    )
    return session, token


def decode_refresh_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SIGNING_KEY,
        algorithms=[settings.JWT_ALG],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )


fernet = Fernet(settings.DATA_ENCRYPTION_KEY or Fernet.generate_key())


def encrypt_str(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()


def decrypt_str(value: str) -> str:  # pragma: no cover
    return fernet.decrypt(value.encode()).decode()


def verify_identity_with_provider(  # pragma: no cover
    national_id: str, date_of_birth: str
) -> dict:
    if not settings.IDENTITY_API_URL:
        return {"verified": True}
    for _ in range(settings.IDENTITY_API_RETRIES):
        try:
            resp = requests.post(
                settings.IDENTITY_API_URL,
                json={"national_id": national_id, "date_of_birth": date_of_birth},
                timeout=settings.IDENTITY_API_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            continue
    raise RuntimeError("identity_provider_error")
