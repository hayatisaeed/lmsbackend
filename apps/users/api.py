import random
import uuid
from datetime import timedelta
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

import jwt
import requests
from django.conf import settings
from django.utils import timezone
from requests.exceptions import RequestException, Timeout

from .models import OTPCode, RefreshSession, User

from datetime import datetime

import logging
logger = logging.getLogger(__name__)


class BaseAPIService:
    """Base class for external API services"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {getattr(settings, 'API_KEY', None)}"
        })
    
    def _make_request(self, url: str, payload: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        """Generic method for making API requests with error handling"""
        try:
            response = self.session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Timeout:
            logger.error(f"API request timed out: {url}")
            raise
        except RequestException as e:
            logger.error(f"API request failed: {url}, error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise


class OTPService(BaseAPIService):
    """Service for handling OTP operations"""
    
    def send_sms_otp(self, code: str, mobile: str, template: Optional[int] = None) -> bool:
        """Send SMS OTP via external provider"""
        payload = {"code": code, "mobile": mobile}
        if template is not None:
            payload["template"] = template
        
        try:
            result = self._make_request(
                f"{settings.OTP_API_URL}/SmsOTP",
                payload
            )
            return result.get('success', False)
        except RequestException:
            # In development, we might want to simulate success
            if settings.DEBUG:
                return True
            return False
    
    def send_call_otp(self, code: str, number: str) -> bool:
        """Send voice OTP via external provider"""
        payload = {"code": code, "number": number}
        
        try:
            result = self._make_request(
                f"{settings.OTP_API_URL}/CallOTP",
                payload
            )
            return result.get('success', False)
        except RequestException:
            if settings.DEBUG:
                return True
            return False


class IdentityService(BaseAPIService):
    """Service for identity verification operations"""
    
    def verify_identity(self, national_code: str, birth_date: str) -> Dict[str, Any]:
        """Verify identity with external provider"""
        if not settings.IDENTITY_API_URL:
            return {"verified": True}
        
        payload = {
            "nationalCode": national_code,
            "birthDate": birth_date  # Format: "1370/1/1"
        }
        
        for attempt in range(settings.IDENTITY_API_RETRIES):
            try:
                result = self._make_request(
                    settings.IDENTITY_API_URL,
                    payload,
                    timeout=settings.IDENTITY_API_TIMEOUT
                )
                
                if result.get('success') and result.get('data'):
                    return {
                        'verified': True,
                        'data': result['data']
                    }
                else:
                    return {
                        'verified': False,
                        'error': result.get('error'),
                        'message': result.get('message')
                    }
                    
            except RequestException as e:
                logger.warning(f"Identity verification attempt {attempt + 1} failed: {str(e)}")
                if attempt == settings.IDENTITY_API_RETRIES - 1:
                    raise RuntimeError("identity_provider_error") from e


class CryptoService:
    """Service for encryption/decryption operations"""
    
    def __init__(self):
        from cryptography.fernet import Fernet
        self.fernet = Fernet(settings.DATA_ENCRYPTION_KEY or Fernet.generate_key())
    
    def encrypt_str(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt_str(self, value: str) -> str:
        return self.fernet.decrypt(value.encode()).decode()


class JWTService:
    """Service for JWT token operations"""
    
    @staticmethod
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
    
    @staticmethod
    def decode_refresh_token(token: str) -> dict:
        return jwt.decode(
            token,
            settings.JWT_SIGNING_KEY,
            algorithms=[settings.JWT_ALG],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )


@dataclass
class OTPResult:
    code: str
    expires_at: datetime
    success: bool


class AuthService:
    """Main service for authentication-related operations"""
    
    def __init__(self):
        self.otp_service = OTPService()
        self.identity_service = IdentityService()
        self.jwt_service = JWTService()
    
    def send_otp(self, phone_number: str, ip: str, method: str = 'sms', 
                template: Optional[int] = None) -> OTPResult:
        """
        Generate and send OTP code to the provided phone number
        
        Args:
            phone_number: Phone number to send OTP to
            ip: Client IP address
            method: 'sms' or 'call'
            template: Template ID for SMS
            
        Returns:
            OTPResult with code, expiration and success status
        """
        # Generate OTP code
        code = "".join(str(random.randint(0, 9)) for _ in range(settings.OTP_LENGTH))
        expires_at = timezone.now() + timedelta(seconds=settings.OTP_TTL_SEC)
        
        # Save to database
        otp = OTPCode.objects.create(
            phone=phone_number,
            code=code,
            purpose="login",
            expires_at=expires_at,
            ip=ip,
        )
        
        # Send via external service
        success = False
        if method == 'call':
            success = self.otp_service.send_call_otp(code, str(phone_number))
        elif method == 'sms':
            success = self.otp_service.send_sms_otp(code, str(phone_number), template)
        else:
            raise ValueError("method must be 'sms' or 'call'")
        
        logger.info(f"OTP {'sent' if success else 'failed'} via {method} to {phone_number}")
        return OTPResult(code=code, expires_at=expires_at, success=success)
    
    def generate_refresh_session(self, user: User, 
                               rotated_from: Optional[RefreshSession] = None) -> Tuple[RefreshSession, str]:
        """Generate refresh session and JWT token"""
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
            "exp": int((timezone.now() + timedelta(seconds=settings.JWT_REFRESH_TTL_SEC)).timestamp()),
            "jti": str(session.jti),
        }
        
        token = jwt.encode(
            token_payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALG
        )
        return session, token
    
    def verify_identity(self, national_id: str, date_of_birth: str) -> Dict[str, Any]:
        """Verify identity with external provider"""
        return self.identity_service.verify_identity(national_id, date_of_birth)


# Initialize services for easy import
otp_service = OTPService()
identity_service = IdentityService()
crypto_service = CryptoService()
jwt_service = JWTService()
auth_service = AuthService()