from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    City,
    EducationalLevel,
    EducationalProfile,
    IdentityInfo,
    Location,
    Olympiad,
    OTPCode,
    ParentContact,
    Province,
    StudyBranch,
)
from .utils import encrypt_str, generate_otp, verify_identity_with_provider

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


class IdentitySerializer(serializers.Serializer):
    national_id = serializers.CharField()
    date_of_birth = serializers.DateField()

    def validate(self, attrs):
        user = self.context["request"].user
        info, _ = IdentityInfo.objects.get_or_create(user=user)
        now = timezone.now()
        if info.last_attempt_at and now - info.last_attempt_at < timedelta(hours=24):
            if info.submission_count >= 5:
                raise serializers.ValidationError("identity_rate_limited")
            info.submission_count += 1
        else:
            info.submission_count = 1
        info.last_attempt_at = now
        info.save(update_fields=["submission_count", "last_attempt_at"])
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        national_id = self.validated_data["national_id"]
        dob = self.validated_data["date_of_birth"].isoformat()
        try:
            data = verify_identity_with_provider(national_id, dob)
        except Exception:
            raise serializers.ValidationError("identity_provider_error") from None
        info, _ = IdentityInfo.objects.get_or_create(user=user)
        info.national_id = encrypt_str(national_id)
        info.date_of_birth = encrypt_str(dob)
        info.first_name = data.get("first_name")
        info.last_name = data.get("last_name")
        info.father_name = data.get("father_name")
        info.gender = data.get("gender")
        info.verified = data.get("verified", True)
        age = (timezone.now().date() - self.validated_data["date_of_birth"]).days // 365
        info.requires_parent = age < settings.AGE_THRESHOLD
        info.save()
        user.profile_identity = True
        user.save(update_fields=["profile_identity"])
        return {"status": "verified"}


class EducationSerializer(serializers.Serializer):
    level = serializers.PrimaryKeyRelatedField(queryset=EducationalLevel.objects.all())
    grade = serializers.IntegerField()
    study_branch = serializers.PrimaryKeyRelatedField(
        queryset=StudyBranch.objects.all(), required=False, allow_null=True
    )
    olympiad_ids = serializers.PrimaryKeyRelatedField(
        queryset=Olympiad.objects.filter(published=True),
        many=True,
        required=False,
    )

    def validate(self, attrs):
        level: EducationalLevel = attrs["level"]
        grade = attrs["grade"]
        if grade < level.min_grade or grade > level.max_grade:
            raise serializers.ValidationError({"grade": "out_of_range"})
        branch = attrs.get("study_branch")
        if level.is_high_school:
            if not branch:
                raise serializers.ValidationError({"study_branch": "required"})
            if branch.level_id != level.id:
                raise serializers.ValidationError({"study_branch": "invalid"})
        olympiads = attrs.get("olympiad_ids", [])
        if len({o.id for o in olympiads}) > 3:
            raise serializers.ValidationError({"olympiad_ids": "too_many"})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        profile, _ = EducationalProfile.objects.update_or_create(
            user=user,
            defaults={
                "level": self.validated_data["level"],
                "grade": self.validated_data["grade"],
                "study_branch": self.validated_data.get("study_branch"),
            },
        )
        if "olympiad_ids" in self.validated_data:
            profile.olympiads.set(self.validated_data["olympiad_ids"])
        user.profile_education = True
        user.save(update_fields=["profile_education"])
        return {"ok": True}


class LocationSerializer(serializers.Serializer):
    province_id = serializers.PrimaryKeyRelatedField(
        queryset=Province.objects.all(), required=False, allow_null=True
    )
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False, allow_null=True
    )
    province = serializers.CharField(required=False)
    city = serializers.CharField(required=False)

    def validate(self, attrs):
        province = attrs.get("province_id")
        city = attrs.get("city_id")
        if not province or not city:
            pname = attrs.get("province")
            cname = attrs.get("city")
            if pname and cname:
                try:
                    province = Province.objects.get(name__iexact=pname)
                    city = City.objects.get(name__iexact=cname, province=province)
                except (Province.DoesNotExist, City.DoesNotExist):
                    raise serializers.ValidationError("location_invalid") from None
            else:
                raise serializers.ValidationError("location_invalid")
        else:
            if city.province_id != province.id:
                raise serializers.ValidationError("location_invalid")
        attrs["province_obj"] = province
        attrs["city_obj"] = city
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        Location.objects.update_or_create(
            user=user,
            defaults={
                "province": self.validated_data["province_obj"],
                "city": self.validated_data["city_obj"],
            },
        )
        user.profile_location = True
        user.save(update_fields=["profile_location"])
        return {"ok": True}


class ParentSerializer(serializers.Serializer):
    phone = serializers.CharField()
    relation = serializers.ChoiceField(choices=["father", "mother", "guardian"])

    def validate_phone(self, value):
        if not value.startswith("+"):
            raise serializers.ValidationError("invalid_phone")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        contact, _ = ParentContact.objects.update_or_create(
            user=user,
            defaults={
                "phone": self.validated_data["phone"],
                "relation": self.validated_data["relation"],
                "verified": False,
                "verified_at": None,
            },
        )
        generate_otp(contact.phone, purpose="parent")
        return {"status": "otp_sent"}


class ParentVerifySerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate(self, attrs):
        user = self.context["request"].user
        try:
            contact = ParentContact.objects.get(user=user)
        except ParentContact.DoesNotExist:
            raise serializers.ValidationError("parent_invalid") from None
        try:
            otp = OTPCode.objects.get(phone=contact.phone, purpose="parent")
        except OTPCode.DoesNotExist:
            raise serializers.ValidationError("parent_otp_invalid") from None
        if timezone.now() > otp.expires_at:
            raise serializers.ValidationError("parent_otp_expired")
        if otp.code != attrs["code"]:
            raise serializers.ValidationError("parent_otp_invalid")
        attrs["otp"] = otp
        attrs["contact"] = contact
        return attrs

    def save(self, **kwargs):
        otp: OTPCode = self.validated_data["otp"]
        contact: ParentContact = self.validated_data["contact"]
        contact.verified = True
        contact.verified_at = timezone.now()
        contact.save(update_fields=["verified", "verified_at"])
        otp.used_at = timezone.now()
        otp.save(update_fields=["used_at"])
        user = self.context["request"].user
        user.profile_parent = True
        user.save(update_fields=["profile_parent"])
        return {"verified": True}


class EducationalLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalLevel
        fields = ["id", "name", "min_grade", "max_grade", "is_high_school"]


class StudyBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyBranch
        fields = ["id", "name", "level", "is_active"]


class OlympiadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Olympiad
        fields = ["id", "name", "olympiad_degree", "published"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "slug"]


class ProvinceListSerializer(serializers.ModelSerializer):
    cities_count = serializers.IntegerField()

    class Meta:
        model = Province
        fields = ["id", "name", "slug", "cities_count"]
