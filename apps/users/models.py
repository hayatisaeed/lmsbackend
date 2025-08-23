import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from django.core.files.storage import default_storage
import os
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone: str, password: str | None, **extra_fields):
        if not phone:
            raise ValueError("The phone must be set")
        phone = phone.strip()
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(phone, password, **extra_fields)


def user_avatar_upload_path(instance, filename):
    """Generate upload path for user avatars"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    return f"avatars/user_{instance.user.id}/{filename}"


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(null=True, blank=True, unique=True)
    roles = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_new_user = models.BooleanField(default=True)
    profile_identity = models.BooleanField(default=False)
    profile_education = models.BooleanField(default=False)
    profile_location = models.BooleanField(default=False)
    profile_parent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def __str__(self) -> str:  # pragma: no cover
        return self.phone

    @property
    def profile_completion(self) -> dict:
        parent_required = False
        try:
            parent_required = self.identityinfo.requires_parent  # type: ignore[attr-defined]
        except IdentityInfo.DoesNotExist:
            pass
        flags = {
            "identity": self.profile_identity,
            "education": self.profile_education,
            "location": self.profile_location,
        }
        if parent_required:
            flags["parent"] = self.profile_parent
        else:
            flags["parent"] = True
        percent = int(sum(1 for v in flags.values() if v) / len(flags) * 100)
        flags["percent_complete"] = percent
        return flags


class OTPCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=10)
    purpose = models.CharField(max_length=20, default="login")
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["phone", "purpose", "expires_at"])]

    def is_valid(self, code: str) -> bool:
        return (
            self.code == code
            and self.used_at is None
            and timezone.now() < self.expires_at
        )


class RefreshSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    jti = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    rotated_from = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        related_name="rotated_to",
        on_delete=models.SET_NULL,
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    def revoke_family(self):
        if self.revoked_at:
            return
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])
        child = getattr(self, "rotated_to", None)
        if child:
            child.revoke_family()

    def rotate(self) -> "RefreshSession":
        new_session = RefreshSession.objects.create(
            user=self.user,
            jti=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(seconds=settings.JWT_REFRESH_TTL_SEC),
            rotated_from=self,
        )
        return new_session


class IdentityInfo(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    national_id = models.CharField(max_length=255)
    date_of_birth = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    father_name = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    verified = models.BooleanField(default=False)
    requires_parent = models.BooleanField(default=False)
    submission_count = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    avatar = models.ImageField(
        upload_to=user_avatar_upload_path,
        null=True,
        blank=True,
        max_length=500,
        help_text="User profile avatar image"
    )
    avatar_thumbnail = models.ImageField(
        upload_to=user_avatar_upload_path,
        null=True,
        blank=True,
        max_length=500,
        help_text="Thumbnail version of avatar"
    )

    def save(self, *args, **kwargs):
        # Delete old files if avatar is being changed
        if self.pk:
            old_instance = User.objects.get(pk=self.pk)
            if old_instance.avatar and old_instance.avatar != self.avatar:
                if default_storage.exists(old_instance.avatar.name):
                    default_storage.delete(old_instance.avatar.name)
                if old_instance.avatar_thumbnail and default_storage.exists(old_instance.avatar_thumbnail.name):
                    default_storage.delete(old_instance.avatar_thumbnail.name)

        # Process new avatar if provided
        if self.avatar and not self.avatar_thumbnail:
            self.create_thumbnail()

        super().save(*args, **kwargs)

    def create_thumbnail(self):
        """Create thumbnail version of the avatar"""
        if not self.avatar:
            return

        # Open image
        img = Image.open(self.avatar)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Create thumbnail
        img.thumbnail((150, 150), Image.Resampling.LANCZOS)
        
        # Save to memory
        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        thumb_io.seek(0)
        
        # Create new filename for thumbnail
        ext = os.path.splitext(self.avatar.name)[1]
        thumb_filename = f"thumb_{uuid.uuid4().hex}.jpg"
        
        # Save thumbnail
        self.avatar_thumbnail.save(
            thumb_filename,
            InMemoryUploadedFile(
                thumb_io,
                None,
                thumb_filename,
                'image/jpeg',
                thumb_io.getbuffer().nbytes,
                None
            ),
            save=False
        )

    def delete(self, *args, **kwargs):
        """Delete associated files when profile is deleted"""
        if self.avatar:
            if default_storage.exists(self.avatar.name):
                default_storage.delete(self.avatar.name)
        if self.avatar_thumbnail:
            if default_storage.exists(self.avatar_thumbnail.name):
                default_storage.delete(self.avatar_thumbnail.name)
        super().delete(*args, **kwargs)


class EducationalLevel(models.Model):
    name = models.CharField(max_length=100)
    min_grade = models.IntegerField(blank=True)
    max_grade = models.IntegerField(blank=True)
    is_high_school = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class StudyBranch(models.Model):
    level = models.ForeignKey(EducationalLevel, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class EducationalGrade(models.Model):
    name = models.CharField(max_length=50)
    level = models.ForeignKey(
        EducationalLevel, related_name="grades", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("name", "level")
        ordering = ["level", "name"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.level.name})"


class Olympiad(models.Model):
    name = models.CharField(max_length=100)
    olympiad_degree = models.IntegerField()
    published = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name

class SchoolType(models.Model):
    name = models.CharField(max_length=25)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}")
        super().save(*args, **kwargs)


class EducationalProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level = models.ForeignKey(EducationalLevel, on_delete=models.CASCADE)
    grade = models.ForeignKey(EducationalGrade, on_delete=models.CASCADE)
    study_branch = models.ForeignKey(
        StudyBranch, on_delete=models.SET_NULL, null=True, blank=True
    )
    olympiads = models.ManyToManyField(Olympiad, blank=True)
    school_name = models.CharField(max_length=100)
    school_type = models.ForeignKey(SchoolType, on_delete=models.PROTECT)

    def clean(self):
        if self.grade.level_id != self.level_id:
            raise ValidationError("grade_invalid_for_level")
        if self.study_branch and self.study_branch.level_id != self.level_id:
            raise ValidationError("study_branch_invalid_for_level")


class Province(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class City(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)

    class Meta:
        unique_together = ("province", "slug")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.province}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Location(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE)


class ParentContact(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    relation = models.CharField(max_length=20)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
