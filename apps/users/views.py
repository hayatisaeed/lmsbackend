from django.conf import settings
from django.core.cache import cache
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RefreshSession, User
from .serializers import RequestOTPSerializer, VerifyOTPSerializer
from .utils import (
    decode_refresh_token,
    generate_access_token,
    generate_otp,
    generate_refresh_session,
)


class APIError(APIException):
    def __init__(self, code: str, status_code: int):
        self.status_code = status_code
        super().__init__(code)


def _incr(key: str, ttl: int) -> int:
    try:
        return cache.incr(key)
    except ValueError:
        cache.add(key, 1, ttl)
        return 1


class RequestOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        ip = request.META.get("REMOTE_ADDR", "unknown")
        cooldown_key = f"otp:cooldown:{phone}"
        if cache.get(cooldown_key):
            raise APIError("otp_throttled", status.HTTP_429_TOO_MANY_REQUESTS)
        if _incr(f"otp:phone:{phone}", 86400) > settings.OTP_MAX_PER_24H_PER_PHONE:
            raise APIError("otp_throttled", status.HTTP_429_TOO_MANY_REQUESTS)
        if _incr(f"otp:ip:{ip}", 3600) > settings.OTP_MAX_PER_HOUR_PER_IP:
            raise APIError("otp_throttled", status.HTTP_429_TOO_MANY_REQUESTS)
        generate_otp(phone, ip)
        cache.set(cooldown_key, 1, settings.OTP_COOLDOWN_SEC)
        user, created = User.objects.get_or_create(phone=phone)
        return Response(
            {
                "is_new_user": created,
                "cooldown_seconds": settings.OTP_COOLDOWN_SEC,
                "next_step_hint": "verify_otp",
            }
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

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

        refresh_cookie_name = str(settings.REFRESH_COOKIE_NAME)
        jwt_refresh_ttl = settings.JWT_REFRESH_TTL_SEC
        cookie_samesite = settings.COOKIE_SAMESITE

        print(f"cookie_name: {refresh_cookie_name}, jwt_ttl: {jwt_refresh_ttl}, cookie_samesite: {cookie_samesite}")
        try:
            #print(f"refresh token: {refresh_token}")
            response.set_cookie(
                key=refresh_cookie_name, 
                value=refresh_token,
                max_age=jwt_refresh_ttl,  # Cookie expires in 1 hour (in seconds)
                httponly=True, # Makes the cookie inaccessible to client-side scripts
                secure=False,  # Set to True if serving over HTTPS
                samesite=cookie_samesite, # Controls cross-site request behavior
                path='/'       # The path for which the cookie is valid
            )
        except Exception as e:
            print(f"related error for coockies: {e}")
        '''
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
        '''
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

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


class LogoutView(APIView):
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


class SessionView(APIView):
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
