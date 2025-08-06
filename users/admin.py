from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    User, IdentityInformation, EducationalLevel, StudyBranch, Olympiad,
    EducationalProfile, Location, ParentContact, OTPCode
)
from .utils import send_otp, generate_parent_verification_code


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['phone', 'display_name', 'email', 'is_profile_complete', 'created_at']
    list_filter = ['is_profile_complete', 'is_active', 'is_staff', 'created_at']
    search_fields = ['phone', 'display_name', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('phone', 'display_name', 'email', 'password')
        }),
        ('Status', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_profile_complete')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EducationalLevel)
class EducationalLevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'min_grade', 'max_grade', 'is_high_school']
    list_filter = ['is_high_school']
    search_fields = ['name']
    ordering = ['min_grade']


@admin.register(StudyBranch)
class StudyBranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'level_name']
    list_filter = ['level', 'level__is_high_school']
    search_fields = ['name', 'level__name']
    ordering = ['level', 'name']
    
    def level_name(self, obj):
        return obj.level.name
    level_name.short_description = 'Level Name'


@admin.register(Olympiad)
class OlympiadAdmin(admin.ModelAdmin):
    list_display = ['name', 'olympiad_degree', 'published']
    list_filter = ['published', 'olympiad_degree']
    search_fields = ['name']
    ordering = ['name']


@admin.register(IdentityInformation)
class IdentityInformationAdmin(admin.ModelAdmin):
    list_display = ['user', 'national_id', 'is_verified', 'submission_count', 'last_submission']
    list_filter = ['is_verified', 'gender', 'created_at']
    search_fields = ['user__display_name', 'user__phone', 'national_id', 'first_name', 'last_name']
    readonly_fields = ['created_at', 'updated_at', 'submission_count', 'last_submission']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Identity Details', {
            'fields': ('national_id', 'date_of_birth', 'first_name', 'last_name', 'father_name', 'gender')
        }),
        ('Verification Status', {
            'fields': ('is_verified', 'submission_count', 'last_submission')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['reset_submission_count']
    
    def reset_submission_count(self, request, queryset):
        updated = queryset.update(submission_count=0, last_submission=None)
        self.message_user(request, f'{updated} identity submissions reset successfully.')
    reset_submission_count.short_description = "Reset submission count"


@admin.register(EducationalProfile)
class EducationalProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'grade', 'study_branch', 'olympiad_count']
    list_filter = ['level', 'level__is_high_school', 'created_at']
    search_fields = ['user__display_name', 'user__phone', 'level__name', 'study_branch__name']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['olympiads']
    ordering = ['-created_at']
    
    def olympiad_count(self, obj):
        return obj.olympiads.count()
    olympiad_count.short_description = 'Olympiads'


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['user', 'province', 'city']
    list_filter = ['province', 'created_at']
    search_fields = ['user__display_name', 'user__phone', 'province', 'city']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(ParentContact)
class ParentContactAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'relation', 'is_verified', 'verification_status']
    list_filter = ['is_verified', 'relation', 'created_at']
    search_fields = ['user__display_name', 'user__phone', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'verification_code', 'verification_expires']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Contact Details', {
            'fields': ('phone', 'relation')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_code', 'verification_expires')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['resend_verification_code', 'verify_contact']
    
    def verification_status(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: green;">✓ Verified</span>')
        elif obj.verification_expires and obj.verification_expires > timezone.now():
            return format_html('<span style="color: orange;">⏳ Pending</span>')
        else:
            return format_html('<span style="color: red;">✗ Expired</span>')
    verification_status.short_description = 'Status'
    
    def resend_verification_code(self, request, queryset):
        updated = 0
        for contact in queryset:
            if not contact.is_verified:
                contact.verification_code = generate_parent_verification_code()
                contact.verification_expires = timezone.now() + timezone.timedelta(minutes=10)
                contact.save()
                updated += 1
        self.message_user(request, f'Verification code resent to {updated} parent contacts.')
    resend_verification_code.short_description = "Resend verification code"
    
    def verify_contact(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} parent contacts verified successfully.')
    verify_contact.short_description = "Mark as verified"


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'code', 'is_used', 'is_expired', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['phone_number']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
    
    actions = ['resend_otp']
    
    def resend_otp(self, request, queryset):
        updated = 0
        for otp in queryset:
            if not otp.is_used:
                new_code = send_otp(otp.phone_number)
                updated += 1
        self.message_user(request, f'OTP resent to {updated} phone numbers.')
    resend_otp.short_description = "Resend OTP"
