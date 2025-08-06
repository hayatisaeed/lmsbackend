from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, phone, display_name, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        user = self.model(phone=phone, display_name=display_name, **extra_fields)
        user.set_password(extra_fields.get('password', None))
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, display_name=None, password=None, **extra_fields):
        if display_name is None:
            display_name = extra_fields.get('display_name')
        if not display_name:
            raise ValueError('The display_name must be set')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('password', password)
        return self.create_user(phone, display_name, **extra_fields)


class User(AbstractUser):
    phone = PhoneNumberField(unique=True, primary_key=True)
    display_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    is_profile_complete = models.BooleanField(default=False)
    state = models.ForeignKey('State', on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey('City', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['display_name']

    objects = UserManager()

    def __str__(self):
        return f"{self.display_name} ({self.phone})"

    def check_profile_completion(self):
        """Check if all required profile sections are completed"""
        try:
            identity = self.identityinformation
            education = self.educationalprofile
            parent_contact = self.parentcontact
            
            # Check if all required sections are completed
            if (identity.is_verified and education and self.state and self.city and parent_contact.is_verified):
                self.is_profile_complete = True
                self.save()
                return True
            else:
                self.is_profile_complete = False
                self.save()
                return False
        except:
            self.is_profile_complete = False
            self.save()
            return False


class EducationalLevel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_high_school = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class StudyBranch(models.Model):
    educational_level = models.ForeignKey(EducationalLevel, on_delete=models.CASCADE, related_name='study_branches')
    name = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ['educational_level', 'name']

    def __str__(self):
        return f"{self.name} ({self.educational_level.name})"


class Olympiad(models.Model):
    name = models.CharField(max_length=200, unique=True)
    published = models.BooleanField(default=True)
    olympiad_degree = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Certificate validity ranking (1-5 scale)"
    )
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Degree: {self.olympiad_degree})"


class IdentityInformation(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='identityinformation')
    national_id = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField()
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    father_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    is_verified = models.BooleanField(default=False)
    submission_count = models.IntegerField(default=0)
    last_submission = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Identity Information"
        verbose_name_plural = "Identity Information"

    def __str__(self):
        return f"{self.user.display_name} - {self.national_id}"

    def can_submit_identity(self):
        """Check if user can submit identity information (rate limiting)"""
        if self.submission_count >= 5:
            # Check if 24 hours have passed since last submission
            if self.last_submission and (timezone.now() - self.last_submission).days < 1:
                return False
            # Reset counter if 24 hours have passed
            self.submission_count = 0
        return True

    def increment_submission_count(self):
        """Increment submission count and update last submission time"""
        self.submission_count += 1
        self.last_submission = timezone.now()
        self.save()


class EducationalGrade(models.Model):
    name = models.CharField(max_length=50)
    education_level = models.ForeignKey(EducationalLevel, related_name="grades", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'education_level')
        ordering = ['education_level', 'name']

    def __str__(self):
        return f"{self.name} ({self.education_level.name})"


class EducationalProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='educationalprofile')
    level = models.ForeignKey(EducationalLevel, on_delete=models.CASCADE)
    grade = models.ForeignKey(EducationalGrade, on_delete=models.CASCADE)
    study_branch = models.ForeignKey(StudyBranch, on_delete=models.CASCADE)
    olympiads = models.ManyToManyField(Olympiad, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Educational Profile"
        verbose_name_plural = "Educational Profiles"

    def __str__(self):
        return f"{self.user.display_name} - {self.level.name} {self.grade.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Ensure grade belongs to level
        if self.grade.education_level != self.level:
            raise ValidationError("Selected grade does not belong to the selected educational level.")
        # Ensure branch belongs to level
        if self.study_branch.educational_level != self.level:
            raise ValidationError("Selected study branch does not belong to the selected educational level.")
        # Ensure all profiles have a study_branch, and for non-high-school levels, it should be 'general'
        if not self.level.is_high_school:
            if self.study_branch.name.lower() != 'general':
                raise ValidationError("For non-high-school levels, the study branch must be 'general'.")
        else:
            # For high school, allow any branch
            pass


class State(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    
    class Meta:
        unique_together = ['name', 'state']
        ordering = ['state', 'name']
    
    def __str__(self):
        return f"{self.name}, {self.state.name}"


class ParentContact(models.Model):
    RELATION_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parentcontact')
    phone = PhoneNumberField()
    relation = models.CharField(max_length=10, choices=RELATION_CHOICES)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True)
    verification_expires = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parent Contact"
        verbose_name_plural = "Parent Contacts"

    def __str__(self):
        return f"{self.user.display_name} - {self.relation} ({self.phone})"


class OTPCode(models.Model):
    phone_number = PhoneNumberField()
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OTP Code"
        verbose_name_plural = "OTP Codes"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone_number} - {self.code}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()
