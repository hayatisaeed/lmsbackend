import random
import uuid
from datetime import timedelta
from typing import Tuple

import jwt
import re
import requests
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone

from .models import OTPCode, RefreshSession, User


def send_otp(phone_number, method='sms', template=None):
    """
    Generate and send OTP code to the provided phone number via external provider.
    
    Args:
        phone_number: PhoneNumberField instance
        method: 'sms' or 'call' - method to send OTP
        template: int or None - template id for SMS
        
    Returns:
        str: The generated OTP code (for testing purposes)
    """
    
    # Regular OTP generation for real phone numbers
    code = str(random.randint(100000, 999999))
    expires_at = timezone.now() + timedelta(minutes=5)

    code, expires_at = generate_otp()
    
    # Create or update OTP record
    OTPCode.objects.update_or_create(
        phone_number=phone_number,
        defaults={
            'code': code, 
            'expires_at': expires_at, 
            'is_used': False
        }
    )
    
    # Send OTP via external provider
    number = str(phone_number)
    # Remove all spaces and non-digit characters
    number = re.sub(r'[^\d]', '', number)
    
    if method == 'call':
        service = 'CallOTP'
        payload = {"code": code, "number": number}
    elif method == 'sms':
        service = 'SmsOTP'
        payload = {"code": code, "mobile": number}
        if template is not None:
            payload["template"] = template
    else:
        raise ValueError("method must be 'sms' or 'call'")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.OTP_API_KEY}"
    }

    try:
        response = requests.post(f"{settings.OTP_API_URL}{service}", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"OTP sent via {method} to {number}: {response.text}")
        print(response.text)
        print(f"Original: {str(phone_number)}, Cleaned: {number}")
    except requests.RequestException as e:
        logger.error(f"OTP sending failed for {number} via {method}: {e} | {getattr(e.response, 'text', '')}")
        # In development, still print the code for testing
        print(f"OTP for {phone_number}: {code} (Expires: {expires_at})")
    
    return code  # Return for testing purposes


def generate_otp(phone: str, ip: str | None = None, purpose: str = "login") -> OTPCode:
    code = "".join(str(random.randint(0, 9)) for _ in range(settings.OTP_LENGTH))
    otp = OTPCode.objects.create(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SEC),
        ip=ip,
    )
    print(f"otp code for phone: {phone} is code: {code}")
    return otp.code, otp.expires_at


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
