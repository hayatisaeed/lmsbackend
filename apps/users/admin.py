from __future__ import annotations

import csv
from typing import Iterable

from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from .models import (
    City,
    EducationalLevel,
    EducationalProfile,
    IdentityInfo,
    Location,
    Olympiad,
    ParentContact,
    Province,
    SchoolType,
    StudyBranch,
    User,
    OTPCode,
)


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "slug")
    list_filter = ("province",)
    search_fields = ("name", "province__name")
    autocomplete_fields = ("province",)


@admin.register(SchoolType)
class SchoolTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


class IdentityInfoInline(admin.StackedInline):
    model = IdentityInfo
    can_delete = False
    extra = 0
    readonly_fields = (
        "masked_national_id",
        "date_of_birth",
        "submission_count",
        "last_attempt_at",
    )

    @admin.display(description="National ID")
    def masked_national_id(self, obj: IdentityInfo) -> str:
        if not obj.national_id:
            return ""
        return f"****{obj.national_id[-4:]}"


class EducationalProfileInline(admin.StackedInline):
    model = EducationalProfile
    can_delete = False
    extra = 0
    autocomplete_fields = ("level", "study_branch")


class LocationInline(admin.StackedInline):
    model = Location
    can_delete = False
    extra = 0
    autocomplete_fields = ("province", "city")


class ParentContactInline(admin.StackedInline):
    model = ParentContact
    can_delete = False
    extra = 0


class ProfileCompleteFilter(admin.SimpleListFilter):
    title = "profile complete"
    parameter_name = "profile_complete"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request: HttpRequest, queryset):
        if self.value() == "yes":
            return queryset.filter(
                profile_identity=True,
                profile_education=True,
                profile_location=True,
                profile_parent=True,
            )
        if self.value() == "no":
            return queryset.exclude(
                profile_identity=True,
                profile_education=True,
                profile_location=True,
                profile_parent=True,
            )
        return queryset


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    inlines = [
        IdentityInfoInline,
        EducationalProfileInline,
        LocationInline,
        ParentContactInline,
    ]
    list_display = (
        "phone",
        "display_name",
        "is_profile_complete",
        "identity_verified",
        "parent_verified",
        "date_joined",
    )
    search_fields = (
        "phone",
        "display_name",
        "email",
        "identityinfo__first_name",
        "identityinfo__last_name",
        "parentcontact__phone",
    )
    list_filter = (
        ProfileCompleteFilter,
        "identityinfo__verified",
        "parentcontact__verified",
        "educationalprofile__level",
        "educationalprofile__study_branch",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50

    actions = [
        "resend_otp",
        "verify_parent_contact",
        "reset_identity_submission_count",
        "export_csv",
    ]

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_active and request.user.is_staff

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.select_related(
            "identityinfo",
            "parentcontact",
            "educationalprofile__level",
            "educationalprofile__study_branch",
        )

    @admin.display(boolean=True)
    def is_profile_complete(self, obj: User) -> bool:
        completion = obj.profile_completion
        return completion.get("percent_complete", 0) == 100

    @admin.display(boolean=True, description="Identity verified")
    def identity_verified(self, obj: User) -> bool:
        try:
            return obj.identityinfo.verified
        except IdentityInfo.DoesNotExist:
            return False

    @admin.display(boolean=True, description="Parent verified")
    def parent_verified(self, obj: User) -> bool:
        try:
            return obj.parentcontact.verified
        except ParentContact.DoesNotExist:
            return False

    @admin.display(description="Date joined")
    def date_joined(self, obj: User):
        return obj.created_at

    @admin.action(description="Resend OTP")
    def resend_otp(self, request: HttpRequest, queryset: Iterable[User]):
        if not request.user.has_perm("users.add_otpcode"):
            self.message_user(request, "Permission denied", level=messages.ERROR)
            return
        for user in queryset:
            self.log_change(request, user, "OTP resend triggered via admin")
        self.message_user(request, f"OTP resend triggered for {queryset.count()} users")

    @admin.action(description="Verify parent contact")
    def verify_parent_contact(self, request: HttpRequest, queryset: Iterable[User]):
        if not request.user.has_perm("users.change_parentcontact"):
            self.message_user(request, "Permission denied", level=messages.ERROR)
            return
        now = timezone.now()
        count = 0
        for user in queryset:
            try:
                pc = user.parentcontact
            except ParentContact.DoesNotExist:
                continue
            pc.verified = True
            pc.verified_at = now
            pc.save(update_fields=["verified", "verified_at"])
            self.log_change(request, pc, "Parent contact verified via admin")
            count += 1
        self.message_user(request, f"Verified parent contact for {count} users")

    @admin.action(description="Reset identity submission count")
    def reset_identity_submission_count(
        self, request: HttpRequest, queryset: Iterable[User]
    ):
        if not request.user.has_perm("users.change_identityinfo"):
            self.message_user(request, "Permission denied", level=messages.ERROR)
            return
        count = 0
        for user in queryset:
            try:
                info = user.identityinfo
            except IdentityInfo.DoesNotExist:
                continue
            info.submission_count = 0
            info.save(update_fields=["submission_count"])
            self.log_change(
                request, info, "Identity submission count reset via admin"
            )
            count += 1
        self.message_user(request, f"Reset submission count for {count} users")

    @admin.action(description="Export CSV")
    def export_csv(self, request: HttpRequest, queryset: Iterable[User]):
        if not request.user.has_perm("users.view_user"):
            self.message_user(request, "Permission denied", level=messages.ERROR)
            return
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=users.csv"
        writer = csv.writer(response)
        writer.writerow([
            "phone",
            "display_name",
            "email",
            "is_profile_complete",
            "level",
            "grade",
        ])
        for user in queryset.select_related(
            "educationalprofile__level",
            "educationalprofile",
        ):
            level_name = (
                user.educationalprofile.level.name
                if getattr(user, "educationalprofile", None)
                else ""
            )
            grade = (
                user.educationalprofile.grade
                if getattr(user, "educationalprofile", None)
                else ""
            )
            writer.writerow(
                [
                    user.phone,
                    user.display_name,
                    user.email,
                    self.is_profile_complete(user),
                    level_name,
                    grade,
                ]
            )
        self.log_change(request, queryset.first() if queryset else None, "Export CSV")
        return response


@admin.register(IdentityInfo)
class IdentityInfoAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "verified",
        "requires_parent",
        "submission_count",
    )
    readonly_fields = (
        "masked_national_id",
        "date_of_birth",
        "submission_count",
        "last_attempt_at",
    )
    search_fields = (
        "user__phone",
        "first_name",
        "last_name",
    )
    autocomplete_fields = ("user",)

    @admin.display(description="National ID")
    def masked_national_id(self, obj: IdentityInfo) -> str:
        if not obj.national_id:
            return ""
        return f"****{obj.national_id[-4:]}"


@admin.register(EducationalLevel)
class EducationalLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "min_grade", "max_grade", "is_high_school")
    search_fields = ("name",)


@admin.register(StudyBranch)
class StudyBranchAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "is_active")
    search_fields = ("name",)
    autocomplete_fields = ("level",)


@admin.register(Olympiad)
class OlympiadAdmin(admin.ModelAdmin):
    list_display = ("name", "olympiad_degree", "published")
    search_fields = ("name",)


@admin.register(EducationalProfile)
class EducationalProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "grade", "study_branch")
    search_fields = (
        "user__phone",
        "user__display_name",
        "level__name",
        "study_branch__name",
    )
    autocomplete_fields = ("user", "level", "study_branch")
    list_select_related = ("user", "level", "study_branch")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("user", "province", "city")
    search_fields = (
        "user__phone",
        "province__name",
        "city__name",
    )
    autocomplete_fields = ("user", "province", "city")
    list_select_related = ("user", "province", "city")


@admin.register(ParentContact)
class ParentContactAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "relation", "verified")
    search_fields = ("user__phone", "phone")
    autocomplete_fields = ("user",)
    list_select_related = ("user",)


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "expires_at", "is_used")
    search_fields = ("phone",)
    readonly_fields = (
        "phone",
        "masked_code",
        "purpose",
        "expires_at",
        "used_at",
        "ip",
        "created_at",
    )
    fields = (
        "phone",
        "masked_code",
        "purpose",
        "expires_at",
        "used_at",
        "ip",
        "created_at",
    )
    actions = ["mark_as_used"]

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_active and request.user.is_staff

    @admin.display(description="Code")
    def masked_code(self, obj: OTPCode) -> str:
        if not obj.code:
            return ""
        return f"****{obj.code[-2:]}"

    @admin.display(boolean=True, description="Used")
    def is_used(self, obj: OTPCode) -> bool:
        return obj.used_at is not None

    @admin.action(description="Mark selected as used")
    def mark_as_used(self, request: HttpRequest, queryset):
        if not request.user.has_perm("users.change_otpcode"):
            self.message_user(request, "Permission denied", level=messages.ERROR)
            return
        now = timezone.now()
        count = 0
        for code in queryset.filter(used_at__isnull=True):
            code.used_at = now
            code.save(update_fields=["used_at"])
            self.log_change(request, code, "Marked as used via admin")
            count += 1
        self.message_user(request, f"Marked {count} codes as used")


