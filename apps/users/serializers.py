from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import OTPCode

User = get_user_model()


class RequestOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value: str) -> str:
        if not value.startswith("+"):
            raise serializers.ValidationError("invalid_phone")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
    display_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        phone = attrs.get("phone")
        code = attrs.get("code")
        try:
            otp = OTPCode.objects.get(phone=phone, purpose="login")
        except OTPCode.DoesNotExist:
            raise serializers.ValidationError("otp_invalid_or_expired") from None
        if not otp.is_valid(code):
            raise serializers.ValidationError("otp_invalid_or_expired")
        attrs["otp_obj"] = otp
        return attrs

    def save(self, **kwargs):
        otp: OTPCode = self.validated_data["otp_obj"]
        user, _created = User.objects.get_or_create(phone=self.validated_data["phone"])
        display_name = self.validated_data.get("display_name")
        if not user.display_name and not display_name:
            raise serializers.ValidationError({"display_name": "required"})
        if display_name:
            user.display_name = display_name
        email = self.validated_data.get("email")
        if email:
            user.email = email
        if "student" not in user.roles:
            user.roles.append("student")
        user.save()
        otp.used_at = timezone.now()
        otp.save(update_fields=["used_at"])
        return user
