from datetime import timedelta
from typing import Any
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    City,
    EducationalGrade,
    EducationalLevel,
    SchoolType,
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
from .api import identity_service, crypto_service

import re
from rest_framework import serializers
from django.core.validators import ValidationError

User = get_user_model()

class PhoneNumberValidator:
    """
    Validator for Iranian phone numbers
    Supports: 09xxxxxxxxx, +989xxxxxxxxx, 989xxxxxxxxx
    """
    message = "invalid_phone_format"
    
    def __call__(self, value):
        # Convert Persian digits to English
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        normalized_value = value.translate(persian_to_english)
        
        # Remove all non-digit characters except +
        cleaned_value = re.sub(r'[^\d+]', '', normalized_value)
        
        # Check if it's a valid Iranian mobile number
        if cleaned_value.startswith('+989') and len(cleaned_value) == 13:
            # +989xxxxxxxxx format
            if not cleaned_value[3:].isdigit() or len(cleaned_value[3:]) != 10:
                raise ValidationError(self.message)
                
        elif cleaned_value.startswith('989') and len(cleaned_value) == 12:
            # 989xxxxxxxxx format
            if not cleaned_value[2:].isdigit() or len(cleaned_value[2:]) != 10:
                raise ValidationError(self.message)
                
        elif cleaned_value.startswith('09') and len(cleaned_value) == 11:
            # 09xxxxxxxxx format
            if not cleaned_value.isdigit():
                raise ValidationError(self.message)
                
        else:
            raise ValidationError(self.message)


class PhoneNumberField(serializers.CharField):
    """
    Serializer field that accepts various phone formats and stores as 09xxxxxxxxx
    """
    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 11)
        super().__init__(**kwargs)
        self.validators.append(PhoneNumberValidator())
    
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        
        # Convert Persian digits to English
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        normalized_value = value.translate(persian_to_english)
        
        # Remove all non-digit characters
        cleaned_value = re.sub(r'[^\d]', '', normalized_value)

        print(cleaned_value)
        
        # Convert to 09xxxxxxxxx format
        if cleaned_value.startswith('989'):
            # 989xxxxxxxxx -> 09xxxxxxxxx
            return '09' + cleaned_value[2:]
        elif cleaned_value.startswith('9'):
            # 9xxxxxxxxx -> 09xxxxxxxxx
            return '0' + cleaned_value
        elif cleaned_value.startswith('09'):
            # Already in correct format
            if len(cleaned_value) == 11:
                return cleaned_value
            else:
                raise ValidationError("invalid_phone_length")
        else:
            # Any other format that passed validation should be 09 + digits
            return '09' + cleaned_value.lstrip('0')
    
    def to_representation(self, value):
        # Return the stored value (09xxxxxxxxx)
        return value


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['display_name', 'email']
    
    def validate_email(self, value):
        """Convert empty email to None and check uniqueness"""
        if value == '':
            value = None
        if value and User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class RequestOTPSerializer(serializers.Serializer):
    phone = PhoneNumberField(required=True)


class VerifyOTPSerializer(serializers.Serializer):
    phone = PhoneNumberField(required=True)
    code = serializers.CharField(max_length=settings.OTP_LENGTH, min_length=settings.OTP_LENGTH)
    display_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        phone = attrs.get("phone")
        code = attrs.get("code")
        try:
            otp = OTPCode.objects.filter(phone=phone, purpose="login").latest('created_at')
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
    national_id = serializers.CharField(min_length=10, max_length=10)
    date_of_birth = serializers.DateField()

    def validate_national_id(self, value):
        """Validate national ID format"""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Invalid national ID format")
        return value

    def validate(self, attrs):
        """Validate submission rate limits"""
        user = self.context["request"].user
        info, _ = IdentityInfo.objects.get_or_create(user=user)
        now = timezone.now()
        
        # Check if user has exceeded submission limits
        if info.last_attempt_at and now - info.last_attempt_at < timedelta(hours=24):
            if info.submission_count >= settings.IDENTITY_MAX_ATTEMPTS:
                raise serializers.ValidationError("identity_rate_limited")
            info.submission_count += 1
        else:
            # Reset counter if more than 24 hours have passed
            info.submission_count = 1
        
        info.last_attempt_at = now
        info.save(update_fields=["submission_count", "last_attempt_at"])
        
        return attrs

    def save(self, **kwargs):
        """Verify identity with external provider and save results"""
        user = self.context["request"].user
        national_id = self.validated_data["national_id"]
        date_of_birth = self.validated_data["date_of_birth"]
        
        # Format date for the external API
        dob_formatted = f"{date_of_birth.year}/{date_of_birth.month}/{date_of_birth.day}"
        
        try:
            # Use the identity service to verify with external provider
            result = identity_service.verify_identity(national_id, dob_formatted)
        except RuntimeError as e:
            #logger.error(f"Identity verification failed for user {user.id}: {str(e)}")
            raise serializers.ValidationError("identity_provider_error")
        except Exception as e:
            #logger.error(f"Unexpected error during identity verification: {str(e)}")
            raise serializers.ValidationError("identity_verification_failed")
        
        # Get or create identity info
        info, created = IdentityInfo.objects.get_or_create(user=user)
        
        # Update identity info with verified data
        if result['verified'] and 'data' in result:
            data = result['data']
            info.national_id = crypto_service.encrypt_str(national_id)
            info.date_of_birth = crypto_service.encrypt_str(dob_formatted)
            info.first_name = data.get("firstName", "")
            info.last_name = data.get("lastName", "")
            info.father_name = data.get("fatherName", "")
            info.gender = data.get("gender", 0)
            info.verified = True
            
            # Calculate age and check if parent is required
            age = (timezone.now().date() - date_of_birth).days // 365
            info.requires_parent = age < getattr(settings, 'AGE_THRESHOLD', 18)
        else:
            # Identity verification failed
            info.verified = False
            error_message = result.get('error') or result.get('message') or 'Verification failed'
            #logger.warning(f"Identity verification failed for user {user.id}: {error_message}")
        
        info.save()
        
        # Update user profile if verified
        if info.verified:
            user.profile_identity = True
            user.save(update_fields=["profile_identity"])
        
        return {
            "status": "verified" if info.verified else "failed",
            "requires_parent": info.requires_parent if info.verified else False,
            "error": None if info.verified else result.get('error')
        }


class SchoolTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolType
        fields = ['name', 'slug']


#### educational profile serializer


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
        province_id = attrs.get("province_id")
        city_id = attrs.get("city_id")
        province_name = attrs.get("province")
        city_name = attrs.get("city")
        
        # If no location data provided, skip validation
        if not any([province_id, city_id, province_name, city_name]):
            return attrs
        
        # Validate province
        if province_id:
            province = province_id
        elif province_name:
            try:
                province = Province.objects.get(name__iexact=province_name)
            except Province.DoesNotExist:
                raise serializers.ValidationError({"province": "invalid"})
        else:
            raise serializers.ValidationError({"province": "required"})
        
        # Validate city
        if city_id:
            city = city_id
            if city.province_id != province.id:
                raise serializers.ValidationError({"city": "invalid_for_province"})
        elif city_name:
            try:
                city = City.objects.get(name__iexact=city_name, province=province)
            except City.DoesNotExist:
                raise serializers.ValidationError({"city": "invalid"})
        else:
            raise serializers.ValidationError({"city": "required"})
        
        attrs["province_obj"] = province
        attrs["city_obj"] = city
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        
        # Only update if location data was provided and validated
        if "province_obj" in self.validated_data and "city_obj" in self.validated_data:
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
    phone = PhoneNumberField(required=True)
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


class EducationalGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalGrade
        fields = ['id', 'name', 'level']


class EducationalProfileSerializer(serializers.ModelSerializer):
    level = EducationalLevelSerializer(read_only=True)
    level_id = serializers.PrimaryKeyRelatedField(
        queryset=EducationalLevel.objects.all(), 
        source='level', 
        write_only=True, 
        required=False,
        allow_null=True
    )
    grade = EducationalGradeSerializer(read_only=True)
    grade_id = serializers.PrimaryKeyRelatedField(
        queryset=EducationalGrade.objects.all(), 
        source='grade', 
        write_only=True, 
        required=False,
        allow_null=True
    )
    study_branch = StudyBranchSerializer(read_only=True)
    study_branch_id = serializers.PrimaryKeyRelatedField(
        queryset=StudyBranch.objects.all(), 
        source='study_branch', 
        write_only=True, 
        required=False,
        allow_null=True
    )
    olympiads = OlympiadSerializer(many=True, read_only=True)
    olympiad_ids = serializers.PrimaryKeyRelatedField(
        queryset=Olympiad.objects.all(), 
        many=True, 
        source='olympiads', 
        write_only=True,
        required=False
    )
    school_type = SchoolTypeSerializer(read_only=True)
    school_type_id = serializers.PrimaryKeyRelatedField(
        queryset=SchoolType.objects.all(), 
        source='school_type', 
        write_only=True,
        required=False
    )
    location = LocationSerializer(source='user.location', read_only=True)
    province_id = serializers.PrimaryKeyRelatedField(
        queryset=Province.objects.all(), 
        write_only=True, 
        required=False
    )
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), 
        write_only=True, 
        required=False
    )
    
    class Meta:
        model = EducationalProfile
        fields = [
            'id', 'level', 'level_id', 'grade', 'grade_id', 'study_branch', 
            'study_branch_id', 'olympiads', 'olympiad_ids', 'school_name', 
            'school_type', 'school_type_id', 'location', 'province_id', 'city_id'
        ]
    
    def validate(self, data):
        # Validate grade matches level if both are provided
        level = data.get('level')
        grade = data.get('grade')
        study_branch = data.get('study_branch')
        
        if grade and level and grade.level != level:
            raise serializers.ValidationError({
                'grade_id': 'Selected grade does not belong to the selected level'
            })
            
        if study_branch and level and study_branch.level != level:
            raise serializers.ValidationError({
                'study_branch_id': 'Selected study branch does not belong to the selected level'
            })
            
        # Validate location if provided
        province = data.get('province_id')
        city = data.get('city_id')
        
        if province and city and city.province != province:
            raise serializers.ValidationError({
                'city_id': 'Selected city does not belong to the selected province'
            })
            
        return data
    
    def create(self, validated_data):
        # Extract location data
        province = validated_data.pop('province_id', None)
        city = validated_data.pop('city_id', None)
        
        # Create educational profile
        profile = EducationalProfile.objects.create(**validated_data)
        
        # Create location if provided
        if province and city:
            Location.objects.create(
                user=profile.user,
                province=province,
                city=city
            )
        
        return profile
    
    def update(self, instance, validated_data):
        # Extract location data
        province = validated_data.pop('province_id', None)
        city = validated_data.pop('city_id', None)
        
        # Update educational profile
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update location if provided
        if province and city:
            location, created = Location.objects.get_or_create(user=instance.user)
            location.province = province
            location.city = city
            location.save()
        
        return instance