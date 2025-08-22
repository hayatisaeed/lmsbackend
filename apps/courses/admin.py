from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from .models import Course

try:  # pragma: no cover - optional models may be absent
    from .models import Enrollment, Lesson
except ImportError:  # pragma: no cover
    Enrollment = None  # type: ignore
    Lesson = None  # type: ignore


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "visibility", "access_mode", "created_at")
    search_fields = ("name",)
    list_filter = ("visibility", "access_mode")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_active and request.user.is_staff


if Lesson is not None:
    class LessonInline(admin.StackedInline):
        model = Lesson
        extra = 0
        autocomplete_fields = ("course",)

    CourseAdmin.inlines = [LessonInline]  # type: ignore[attr-defined]

    @admin.register(Lesson)
    class LessonAdmin(admin.ModelAdmin):
        list_display = ("course", "title", "order")
        search_fields = ("title", "course__name")
        list_select_related = ("course",)
        autocomplete_fields = ("course",)

        def has_module_permission(self, request: HttpRequest) -> bool:
            return request.user.is_active and request.user.is_staff


if Enrollment is not None:
    @admin.register(Enrollment)
    class EnrollmentAdmin(admin.ModelAdmin):
        list_display = ("user", "course", "created_at")
        search_fields = ("user__phone", "course__name")
        list_select_related = ("user", "course")
        autocomplete_fields = ("user", "course")

        def has_module_permission(self, request: HttpRequest) -> bool:
            return request.user.is_active and request.user.is_staff

