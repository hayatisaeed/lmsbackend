from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from .models import *

try:  # pragma: no cover - optional models may be absent
    from .models import Enrollment, Lesson
except ImportError:  # pragma: no cover
    Enrollment = None  # type: ignore
    Lesson = None  # type: ignore


class ExamAssignmentInline(admin.TabularInline):
    model = ExamAssignment
    extra = 1
    fields = ('exam', 'start_at', 'end_at', 'duration_override', 'reuse_last_user_result')

class QuestionFileInline(admin.TabularInline):
    model = QuestionFile
    extra = 1

class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 4
    fields = ('text', 'is_correct', 'order_index', 'feedback')

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ('type', 'title', 'order_index', 'correct_score', 'wrong_score')
    inlines = [QuestionFileInline, MCQOptionInline]  # Nested not directly supported; use custom template or separate

class GraderAssignmentInline(admin.TabularInline):
    model = GraderAssignment
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'visibility', 'access_mode', 'created_at')
    list_filter = ('visibility', 'access_mode')
    inlines = [ExamAssignmentInline]
    filter_horizontal = ('participants',)

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'allow_negative_scoring')
    inlines = [QuestionInline, GraderAssignmentInline]
    fieldsets = (
        (None, {'fields': ('title', 'description', 'status', 'created_by')}),
        ('Scoring', {'fields': ('default_correct_score', 'default_wrong_score', 'allow_negative_scoring', 'min_accept_score')}),
        ('Settings', {'fields': ('duration_minutes', 'attempt_limit', 'auto_grade_if_all_mcq', 'hide_autograded_until_release')}),
    )

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam', 'type', 'order_index')
    list_filter = ('type', 'exam')
    inlines = [MCQOptionInline, QuestionFileInline]
    fieldsets = (
        (None, {'fields': ('exam', 'type', 'title', 'body_richtext', 'order_index')}),
        ('Scoring', {'fields': ('correct_score', 'wrong_score', 'partial_scoring')}),
        ('File Options', {'fields': ('answer_accepts_file_types', 'answer_max_files', 'is_required')}),
    )

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

