from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    User, IdentityInformation, EducationalLevel, StudyBranch, Olympiad,
    EducationalProfile, State, City, ParentContact, OTPCode
)
from .utils import send_otp, verify_otp, generate_parent_verification_code
from phonenumber_field.serializerfields import PhoneNumberField as DRFPhoneNumberField
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


class UserSerializer(serializers.ModelSerializer):
    phone = DRFPhoneNumberField(help_text="User's phone number in international format")
    state_name = serializers.CharField(source='state.name', read_only=True, help_text="State name")
    city_name = serializers.CharField(source='city.name', read_only=True, help_text="City name")
    class Meta:
        model = User
        fields = ['phone', 'display_name', 'email', 'is_profile_complete', 'state', 'state_name', 'city', 'city_name', 'created_at']
        read_only_fields = ['is_profile_complete', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    phone = DRFPhoneNumberField(help_text="User's phone number in international format (e.g., +989123456789)")
    display_name = serializers.CharField(help_text="User's display name (optional)", max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, help_text="User's email address (optional)", allow_blank=True)
    password = serializers.CharField(write_only=True, help_text="User's password (optional)", min_length=8, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['phone', 'display_name', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'email': {'required': False},
            'display_name': {'required': False}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class OTPRequestSerializer(serializers.Serializer):
    phone = DRFPhoneNumberField(help_text="Phone number to send OTP to (e.g., +989123456789)")

    def validate_phone(self, value):
        try:
            from phonenumber_field.phonenumber import to_python
            phone_number = to_python(value, region='IR')
            if not phone_number or not phone_number.is_valid():
                raise serializers.ValidationError("Invalid phone number format")
            return phone_number
        except Exception:
            raise serializers.ValidationError("Invalid phone number format")

    def create(self, validated_data):
        phone = validated_data['phone']
        otp_code = send_otp(phone)
        return {'phone': str(phone), 'message': 'OTP sent successfully'}


class OTPVerificationSerializer(serializers.Serializer):
    phone = DRFPhoneNumberField(help_text="Phone number that received the OTP")
    code = serializers.CharField(max_length=6, help_text="6-digit OTP code")
    display_name = serializers.CharField(help_text="User's display name (optional)", max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(help_text="User's email address (optional)", required=False, allow_blank=True)
    password = serializers.CharField(help_text="User's password (optional)", min_length=8, required=False, allow_blank=True)

    def validate_phone(self, value):
        try:
            from phonenumber_field.phonenumber import to_python
            phone_number = to_python(value, region='IR')
            if not phone_number or not phone_number.is_valid():
                raise serializers.ValidationError("Invalid phone number format")
            return phone_number
        except Exception:
            raise serializers.ValidationError("Invalid phone number format")

    def validate(self, data):
        phone = data['phone']
        code = data['code']
        if not verify_otp(phone, code):
            raise serializers.ValidationError("Invalid or expired OTP code")
        return data

    def create(self, validated_data):
        phone = validated_data['phone']
        code = validated_data['code']
        
        # Remove code from validated_data as it's not needed for user creation
        user_data = {k: v for k, v in validated_data.items() if k not in ['phone', 'code']}
        
        # Get or create user
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults=user_data
        )
        
        # If user exists, update optional fields if provided
        if not created and user_data:
            for field, value in user_data.items():
                if value:  # Only update if value is provided
                    setattr(user, field, value)
            user.save()
        
        return user


class PasswordLoginSerializer(serializers.Serializer):
    phone = DRFPhoneNumberField(help_text="User's phone number")
    password = serializers.CharField(write_only=True, help_text="User's password")

    def validate_phone(self, value):
        try:
            from phonenumber_field.phonenumber import to_python
            phone_number = to_python(value, region='IR')
            if not phone_number or not phone_number.is_valid():
                raise serializers.ValidationError("Invalid phone number format")
            return phone_number
        except Exception:
            raise serializers.ValidationError("Invalid phone number format")


class EducationalLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalLevel
        fields = '__all__'


class StudyBranchSerializer(serializers.ModelSerializer):
    level_name = serializers.CharField(source='educational_level.name', read_only=True, help_text="Educational level name")
    
    class Meta:
        model = StudyBranch
        fields = ['id', 'educational_level', 'level_name', 'name']


class OlympiadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Olympiad
        fields = '__all__'


class IdentityInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityInformation
        fields = [
            'national_id', 'date_of_birth', 'first_name', 'last_name',
            'father_name', 'gender', 'is_verified', 'submission_count'
        ]
        read_only_fields = ['is_verified', 'submission_count']

    def validate(self, data):
        user = self.context['request'].user
        
        # Check rate limiting
        try:
            identity = user.identityinformation
            if not identity.can_submit_identity():
                raise serializers.ValidationError(
                    "Maximum 5 identity submissions per day. Please try again tomorrow."
                )
        except IdentityInformation.DoesNotExist:
            pass
        
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        identity, created = IdentityInformation.objects.get_or_create(
            user=user,
            defaults=validated_data
        )
        
        if not created:
            for attr, value in validated_data.items():
                setattr(identity, attr, value)
            identity.save()
        
        # Increment submission count
        identity.increment_submission_count()
        
        # Simulate API call to fetch additional information
        # In production, this would be an actual API call
        if not identity.first_name:
            identity.first_name = "API_Fetched_First_Name"
            identity.last_name = "API_Fetched_Last_Name"
            identity.father_name = "API_Fetched_Father_Name"
            identity.gender = "M"
            identity.is_verified = True
            identity.save()
        
        return identity


class EducationalProfileSerializer(serializers.ModelSerializer):
    level_name = serializers.CharField(source='level.name', read_only=True)
    study_branch_name = serializers.CharField(source='study_branch.name', read_only=True)
    olympiads = OlympiadSerializer(many=True, read_only=True)
    olympiad_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Olympiad.objects.filter(published=True),
        source='olympiads',
        required=False
    )
    
    class Meta:
        model = EducationalProfile
        fields = [
            'level', 'level_name', 'grade', 'study_branch', 'study_branch_name',
            'olympiads', 'olympiad_ids'
        ]

    def validate(self, data):
        level = data.get('level')
        grade = data.get('grade')
        study_branch = data.get('study_branch')
        olympiads = data.get('olympiads', [])
        
        # Validate grade within level range
        if level and grade:
            if grade < level.min_grade or grade > level.max_grade:
                raise serializers.ValidationError(
                    f'Grade must be between {level.min_grade} and {level.max_grade} for {level.name}'
                )
        
        # Validate study branch for high school levels
        if level and level.is_high_school and not study_branch:
            raise serializers.ValidationError('Study branch is required for high school levels')
        
        # Validate olympiad limit
        if len(olympiads) > 3:
            raise serializers.ValidationError('Maximum 3 olympiads allowed per user')
        
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        profile, created = EducationalProfile.objects.get_or_create(
            user=user,
            defaults=validated_data
        )
        
        if not created:
            for attr, value in validated_data.items():
                if attr != 'olympiads':
                    setattr(profile, attr, value)
            profile.save()
            
            # Update olympiads separately
            if 'olympiads' in validated_data:
                profile.olympiads.set(validated_data['olympiads'])
        
        return profile


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name']


class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state.name', read_only=True, help_text="State name")
    
    class Meta:
        model = City
        fields = ['id', 'name', 'state', 'state_name']


class ParentContactSerializer(serializers.ModelSerializer):
    phone = DRFPhoneNumberField()
    class Meta:
        model = ParentContact
        fields = ['phone', 'relation', 'is_verified']

    def validate_phone(self, value):
        try:
            from phonenumber_field.phonenumber import to_python
            phone_number = to_python(value, region='IR')
            if not phone_number or not phone_number.is_valid():
                raise serializers.ValidationError("Invalid phone number format")
            return phone_number
        except Exception:
            raise serializers.ValidationError("Invalid phone number format")

    def create(self, validated_data):
        user = self.context['request'].user
        
        # Generate verification code
        verification_code = generate_parent_verification_code()
        expires_at = timezone.now() + timezone.timedelta(minutes=10)
        
        parent_contact, created = ParentContact.objects.get_or_create(
            user=user,
            defaults={
                **validated_data,
                'verification_code': verification_code,
                'verification_expires': expires_at
            }
        )
        
        if not created:
            for attr, value in validated_data.items():
                setattr(parent_contact, attr, value)
            parent_contact.verification_code = verification_code
            parent_contact.verification_expires = expires_at
            parent_contact.save()
        
        # In production: Send SMS with verification code
        print(f"Parent verification code for {parent_contact.phone}: {verification_code}")
        
        return parent_contact


class ParentVerificationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        user = self.context['request'].user
        code = data['code']
        
        try:
            parent_contact = user.parentcontact
            if parent_contact.verification_code != code:
                raise serializers.ValidationError("Invalid verification code")
            
            if parent_contact.verification_expires < timezone.now():
                raise serializers.ValidationError("Verification code has expired")
            
            parent_contact.is_verified = True
            parent_contact.save()
            
        except ParentContact.DoesNotExist:
            raise serializers.ValidationError("No parent contact found for this user")
        
        return data


class ProfileCompletionSerializer(serializers.Serializer):
    """Serializer to check profile completion status"""
    is_profile_complete = serializers.BooleanField(read_only=True)
    identity_completed = serializers.BooleanField(read_only=True)
    education_completed = serializers.BooleanField(read_only=True)
    location_completed = serializers.BooleanField(read_only=True)
    parent_completed = serializers.BooleanField(read_only=True) 