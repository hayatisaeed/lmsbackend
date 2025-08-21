from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class Course(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    class AccessMode(models.TextChoices):
        FREE = "free", "Free"
        PURCHASE = "purchase", "Purchase"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    banner_image = models.URLField(blank=True)
    index_image = models.URLField(blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    access_mode = models.CharField(
        max_length=20, choices=AccessMode.choices, default=AccessMode.FREE
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="courses", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Exam(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    default_correct_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("1.0")
    )
    default_wrong_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.0")
    )
    allow_negative_scoring = models.BooleanField(default=False)
    duration_minutes = models.IntegerField(null=True, blank=True)
    attempt_limit = models.IntegerField(default=1)
    auto_grade_if_all_mcq = models.BooleanField(default=False)
    min_accept_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.0")
    )
    total_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    accept_even_below_min = models.BooleanField(default=False)
    show_score_if_passed = models.BooleanField(default=True)
    show_score_if_failed = models.BooleanField(default=True)
    hide_autograded_until_release = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exams"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.title


class ExamAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="assignments")
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="exam_assignments"
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    duration_override = models.IntegerField(null=True, blank=True)
    reuse_last_user_result = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("exam", "course")


class Question(models.Model):
    class Type(models.TextChoices):
        MCQ = "MCQ", "Multiple Choice"
        TEXT = "TEXT", "Text"
        FILE = "FILE", "File"
        TEXT_OR_FILE = "TEXT_OR_FILE", "Text or File"

    class FileTypes(models.TextChoices):
        IMAGES_ONLY = "images_only", "Images only"
        IMAGES_AND_PDF = "images+pdf", "Images and PDF"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    type = models.CharField(max_length=20, choices=Type.choices)
    title = models.CharField(max_length=255)
    body_richtext = models.TextField(blank=True)
    order_index = models.IntegerField()
    correct_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    wrong_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    partial_scoring = models.BooleanField(default=False)
    answer_accepts_file_types = models.CharField(
        max_length=20, choices=FileTypes.choices, default=FileTypes.IMAGES_ONLY
    )
    answer_max_files = models.IntegerField(default=1)
    is_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_index"]


class QuestionFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="assets"
    )
    title = models.CharField(max_length=255, blank=True)
    file = models.URLField()


class MCQOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order_index = models.IntegerField()
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ["order_index"]


class Attempt(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"
        GRADED = "graded", "Graded"
        RELEASED = "released", "Released"
        EXPIRED = "expired", "Expired"
        VOID = "void", "Void"

    class ResultVisibility(models.TextChoices):
        VISIBLE = "visible", "Visible"
        HIDDEN = "hidden", "Hidden"
        PENDING = "pending", "Pending"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts"
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="attempts"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NOT_STARTED
    )
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    final_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    is_passed = models.BooleanField(default=False)
    autograded = models.BooleanField(default=False)
    result_visibility_state = models.CharField(
        max_length=20,
        choices=ResultVisibility.choices,
        default=ResultVisibility.PENDING,
    )
    time_spent_seconds = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "exam", "course"],
                name="unique_attempt_per_user_exam_course",
            )
        ]


class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        Attempt, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    final_payload = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(null=True, blank=True)


class AnswerFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE, related_name="files"
    )
    file = models.URLField()
    title = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class GradingItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GRADED = "graded", "Graded"
        CONFIRMED = "confirmed", "Confirmed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE, related_name="grading_items"
    )
    grader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grading_items",
    )
    score_awarded = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.0")
    )
    feedback = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    graded_at = models.DateTimeField(null=True, blank=True)


class GraderAssignment(models.Model):
    class Scope(models.TextChoices):
        ENTIRE_EXAM = "entire_exam", "Entire exam"
        SUBSET_QUESTIONS = "subset_questions", "Subset of questions"
        SUBSET_ATTEMPTS = "subset_attempts", "Subset of attempts"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="grader_assignments"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grader_assignments",
    )
    scope = models.CharField(max_length=20, choices=Scope.choices)
    created_at = models.DateTimeField(auto_now_add=True)


__all__ = [
    "Course",
    "Exam",
    "ExamAssignment",
    "Question",
    "QuestionFile",
    "MCQOption",
    "Attempt",
    "Answer",
    "AnswerFile",
    "GradingItem",
    "GraderAssignment",
]
