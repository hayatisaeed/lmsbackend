from django.conf import settings
from django.core.cache import cache
from django.middleware.csrf import get_token
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RefreshSession, User
from .serializers import RequestOTPSerializer, VerifyOTPSerializer
from .utils import (
    decode_refresh_token,
    generate_access_token,
    generate_otp,
    send_otp,
    generate_refresh_session,
)


from .api import auth_service
import logging

logger = logging.getLogger(__name__)

class APIError(APIException):
    def __init__(self, code: str, status_code: int):
        self.status_code = status_code
        super().__init__(code)


def _incr(key, timeout):
    """Helper function to increment cache value with timeout"""
    value = cache.get(key, 0) + 1
    cache.set(key, value, timeout)
    return value


@extend_schema(tags=["Auth"])
class RequestOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RequestOTPSerializer,
        responses={
            200: OpenApiResponse(description="OTP sent successfully"),
            400: OpenApiResponse(description="Invalid input"),
            429: OpenApiResponse(description="Too many requests"),
        },
    )
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone = serializer.validated_data["phone"]
        ip = request.META.get("REMOTE_ADDR", "unknown")
        method = serializer.validated_data.get("method", "sms")
        template = serializer.validated_data.get("template")
        
        # Rate limiting checks
        cooldown_key = f"otp:cooldown:{phone}"
        if cache.get(cooldown_key):
            logger.warning(f"OTP request throttled for phone {phone} (cooldown)")
            raise APIError("otp_throttled", status.HTTP_429_TOO_MANY_REQUESTS)
            
        # Check daily limit per phone
        daily_phone_key = f"otp:phone:{phone}"
        if _incr(daily_phone_key, 86400) > settings.OTP_MAX_PER_24H_PER_PHONE:
            logger.warning(f"OTP daily limit exceeded for phone {phone}")
            raise APIError("otp_throttled", status.HTTP_429_TOO_MANY_REQUESTS)
            
        # Check hourly limit per IP
        hourly_ip_key = f"otp:ip:{ip}"
        if _incr(hourly_ip_key, 3600) > settings.OTP_MAX_PER_HOUR_PER_IP:
            logger.warning(f"OTP hourly limit exceeded for IP {ip}")
            raise APIError("otp_throttled", status.HTTP_429_TOO_MANY_REQUESTS)
        
        try:
            # Send OTP using the auth service
            result = auth_service.send_otp(phone, ip, method, template)
            
            if not result.success:
                logger.error(f"OTP sending failed for phone {phone}")
                raise APIError("otp_send_failed", status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            # Set cooldown period
            cache.set(cooldown_key, 1, settings.OTP_COOLDOWN_SEC)
            
            # Get or create user
            user, created = User.objects.get_or_create(phone=phone)
            
            return Response({
                "is_new_user": created,
                "cooldown_seconds": settings.OTP_COOLDOWN_SEC,
                "next_step_hint": "verify_otp",
                "method": method,
            })
            
        except Exception as e:
            logger.error(f"Unexpected error in OTP request: {str(e)}")
            raise APIError("otp_send_failed", status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=["Auth"])
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: OpenApiResponse(description="OTP verified")},
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        access_token, ttl = generate_access_token(user)
        session, refresh_token = generate_refresh_session(user)
        response = Response(
            {
                "access_token": access_token,
                "access_expires_in": ttl,
                "is_new_user": user.is_new_user,
                "profile_completion": user.profile_completion,
            }
        )

        response.set_cookie(
            settings.REFRESH_COOKIE_NAME,
            refresh_token,
            max_age=settings.JWT_REFRESH_TTL_SEC,
            httponly=True,
            secure=True,
            samesite=settings.COOKIE_SAMESITE,
            path="/",
        )
        response.set_cookie(
            settings.CSRF_COOKIE_NAME,
            get_token(request),
            httponly=False,
            secure=True,
            samesite=settings.COOKIE_SAMESITE,
        )
        return response


@extend_schema(tags=["Auth"])
class RefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Token refreshed"),
            401: OpenApiResponse(description="Invalid refresh token"),
            409: OpenApiResponse(description="Token family revoked"),
            419: OpenApiResponse(description="Rotation required"),
        }
    )
    def post(self, request):
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not token:
            raise APIError("auth_invalid_refresh", status.HTTP_401_UNAUTHORIZED)
        try:
            payload = decode_refresh_token(token)
        except Exception:
            raise APIError(
                "auth_invalid_refresh", status.HTTP_401_UNAUTHORIZED
            ) from None
        jti = payload.get("jti")
        user_id = payload.get("sub")
        try:
            session = RefreshSession.objects.get(jti=jti, user_id=user_id)
        except RefreshSession.DoesNotExist:
            raise APIError(
                "auth_invalid_refresh", status.HTTP_401_UNAUTHORIZED
            ) from None
        if session.revoked_at:
            raise APIError("auth_family_revoked", status.HTTP_409_CONFLICT)
        if hasattr(session, "rotated_to"):
            session.revoke_family()
            raise APIError("auth_rotation_required", 419)
        new_session, refresh_token = generate_refresh_session(session.user, session)
        access_token, ttl = generate_access_token(session.user)
        response = Response({"access_token": access_token, "access_expires_in": ttl})
        response.set_cookie(
            settings.REFRESH_COOKIE_NAME,
            refresh_token,
            max_age=settings.JWT_REFRESH_TTL_SEC,
            httponly=True,
            secure=True,
            samesite=settings.COOKIE_SAMESITE,
            path="/",
        )
        response.set_cookie(
            settings.CSRF_COOKIE_NAME,
            get_token(request),
            httponly=False,
            secure=True,
            samesite=settings.COOKIE_SAMESITE,
        )
        return response


@extend_schema(tags=["Auth"])
class LogoutView(APIView):
    @extend_schema(responses={204: OpenApiResponse(description="Logged out")})
    def post(self, request):
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if token:
            try:
                payload = decode_refresh_token(token)
                session = RefreshSession.objects.get(jti=payload.get("jti"))
                session.revoke_family()
            except Exception:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/")
        return response


@extend_schema(tags=["Auth"])
class SessionView(APIView):
    parser_classes = [IsAuthenticated]
    @extend_schema(
        responses={200: OpenApiResponse(description="Current session info")}
    )
    def get(self, request):
        user: User = request.user  # type: ignore
        data = {
            "user": {
                "id": str(user.id),
                "phone": user.phone,
                "display_name": user.display_name,
                "email": user.email,
                "roles": user.roles,
            },
            "profile_completion": user.profile_completion,
            "is_new_user": user.is_new_user,
        }
        if user.is_new_user:
            user.is_new_user = False
            user.save(update_fields=["is_new_user"])
        return Response(data)
