import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


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


class EducationalLevel(models.Model):
    name = models.CharField(max_length=100)
    min_grade = models.IntegerField()
    max_grade = models.IntegerField()
    is_high_school = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class StudyBranch(models.Model):
    level = models.ForeignKey(EducationalLevel, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Olympiad(models.Model):
    name = models.CharField(max_length=100)
    olympiad_degree = models.IntegerField()
    published = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class EducationalProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level = models.ForeignKey(EducationalLevel, on_delete=models.CASCADE)
    grade = models.IntegerField()
    study_branch = models.ForeignKey(
        StudyBranch, on_delete=models.SET_NULL, null=True, blank=True
    )
    olympiads = models.ManyToManyField(Olympiad, blank=True)


class Province(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class City(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    class Meta:
        unique_together = ("province", "slug")

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
