from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .models import Attempt, Course, Exam, GraderAssignment


class IsEnrolledInCourse(BasePermission):
    message = "You are not enrolled in this course"

    def has_permission(self, request: Request, view) -> bool:
        course_id = view.kwargs.get("course_id") if hasattr(view, "kwargs") else None
        if course_id is None:
            course_id = request.data.get("course")
        if course_id is None:
            return True
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return False
        return course.participants.filter(id=request.user.id).exists()

    def has_object_permission(self, request: Request, view, obj) -> bool:
        course = getattr(obj, "course", None)
        if course is None and isinstance(obj, Course):
            course = obj
        if course is None:
            return False
        return course.participants.filter(id=request.user.id).exists()


class IsExamAdmin(BasePermission):
    message = "You do not have admin access to this exam"

    def has_object_permission(self, request: Request, view, obj) -> bool:
        exam = obj if isinstance(obj, Exam) else getattr(obj, "exam", None)
        if exam is None:
            return False
        return exam.created_by_id == request.user.id


class IsGrader(BasePermission):
    message = "You are not a grader for this exam"

    def has_object_permission(self, request: Request, view, obj) -> bool:
        exam = obj if isinstance(obj, Exam) else getattr(obj, "exam", None)
        if exam is None:
            exam = getattr(getattr(obj, "question", None), "exam", None)
        if exam is None:
            return False
        if exam.created_by_id == request.user.id:
            return True
        return GraderAssignment.objects.filter(
            exam=exam, teacher=request.user
        ).exists()


class IsAttemptOwner(BasePermission):
    message = "You do not own this attempt"

    def has_object_permission(self, request: Request, view, obj) -> bool:
        attempt = obj if isinstance(obj, Attempt) else getattr(obj, "attempt", None)
        if attempt is None:
            return False
        return attempt.user_id == request.user.id
