import uuid
from typing import Any, Tuple

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request) -> Tuple[Any, str] | None:
        header = authentication.get_authorization_header(request).decode()
        if not header or not header.startswith(f"{self.keyword} "):
            return None
        token = header[len(self.keyword) + 1 :]
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SIGNING_KEY,
                algorithms=[settings.JWT_ALG],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
            )
        except jwt.PyJWTError:
            raise exceptions.AuthenticationFailed("invalid_token") from None
        user_id = payload.get("sub")
        if not user_id:
            raise exceptions.AuthenticationFailed("invalid_token")
        try:
            user = User.objects.get(id=uuid.UUID(user_id))
        except (User.DoesNotExist, ValueError):
            raise exceptions.AuthenticationFailed("user_not_found") from None
        if not user.is_active:
            raise exceptions.AuthenticationFailed("user_inactive")
        return (user, token)

    def authenticate_header(self, request) -> str:
        return self.keyword
