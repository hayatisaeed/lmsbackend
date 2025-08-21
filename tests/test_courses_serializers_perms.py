from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory

from apps.courses import models as m
from apps.courses import serializers as s
from apps.users.models import User


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(phone="+10000000000")


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(phone="+10000000001")


@pytest.fixture
def course(db):
    return m.Course.objects.create(name="Math", description="desc")


@pytest.fixture
def exam(user, db):
    return m.Exam.objects.create(title="Final", created_by=user)


def start_serializer_data(exam, course):
    return {"exam": exam.id, "course": course.id}


def test_question_edit_locked_after_publish_with_attempts(user, exam, course):
    q = m.Question.objects.create(
        exam=exam, type=m.Question.Type.TEXT, title="Q1", order_index=1
    )
    exam.status = m.Exam.Status.PUBLISHED
    exam.save()
    m.ExamAssignment.objects.create(
        exam=exam,
        course=course,
        start_at=timezone.now(),
        end_at=timezone.now(),
        duration_override=10,
    )
    course.participants.add(user)
    m.Attempt.objects.create(user=user, exam=exam, course=course)
    serializer = s.QuestionSerializer(
        instance=q,
        data={"title": "new title", "type": q.type, "order_index": 1},
    )
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_mcq_option_single_correct_validation(exam):
    q = m.Question.objects.create(
        exam=exam, type=m.Question.Type.MCQ, title="Q1", order_index=1
    )
    m.MCQOption.objects.create(
        question=q, text="A", is_correct=True, order_index=1
    )
    serializer = s.MCQOptionSerializer(
        data={
            "question": q.id,
            "text": "B",
            "is_correct": True,
            "order_index": 2,
        }
    )
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_exam_assignment_validation(exam, course):
    now = timezone.now()
    serializer = s.ExamAssignmentSerializer(
        data={
            "exam": exam.id,
            "course": course.id,
            "start_at": now,
            "end_at": now,
            "duration_override": 10,
        }
    )
    assert not serializer.is_valid()
    m.ExamAssignment.objects.create(
        exam=exam,
        course=course,
        start_at=now,
        end_at=now + timedelta(hours=1),
    )
    serializer = s.ExamAssignmentSerializer(
        data={
            "exam": exam.id,
            "course": course.id,
            "start_at": now,
            "end_at": now + timedelta(hours=2),
        }
    )
    assert not serializer.is_valid()


def test_attempt_start_requires_enrollment(factory, other_user, exam, course):
    m.ExamAssignment.objects.create(
        exam=exam,
        course=course,
        start_at=timezone.now() - timedelta(minutes=5),
        end_at=timezone.now() + timedelta(minutes=5),
        duration_override=5,
    )
    request = factory.post("/start")
    request.user = other_user
    serializer = s.AttemptStartSerializer(
        data=start_serializer_data(exam, course),
        context={"request": request},
    )
    with pytest.raises(PermissionDenied):
        serializer.is_valid(raise_exception=True)


def test_attempt_start_outside_window(factory, user, exam, course):
    start = timezone.now() + timedelta(days=1)
    m.ExamAssignment.objects.create(
        exam=exam,
        course=course,
        start_at=start,
        end_at=start + timedelta(days=1),
        duration_override=5,
    )
    course.participants.add(user)
    request = factory.post("/start")
    request.user = user
    serializer = s.AttemptStartSerializer(
        data=start_serializer_data(exam, course),
        context={"request": request},
    )
    with pytest.raises(PermissionDenied):
        serializer.is_valid(raise_exception=True)


def test_attempt_start_missing_duration(factory, user, exam, course):
    now = timezone.now()
    m.ExamAssignment.objects.create(
        exam=exam,
        course=course,
        start_at=now - timedelta(minutes=5),
        end_at=now + timedelta(minutes=5),
    )
    course.participants.add(user)
    request = factory.post("/start")
    request.user = user
    serializer = s.AttemptStartSerializer(
        data=start_serializer_data(exam, course),
        context={"request": request},
    )
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_attempt_start_duplicate(factory, user, exam, course):
    now = timezone.now()
    m.ExamAssignment.objects.create(
        exam=exam,
        course=course,
        start_at=now - timedelta(minutes=5),
        end_at=now + timedelta(minutes=5),
        duration_override=5,
    )
    course.participants.add(user)
    m.Attempt.objects.create(user=user, exam=exam, course=course)
    request = factory.post("/start")
    request.user = user
    serializer = s.AttemptStartSerializer(
        data=start_serializer_data(exam, course),
        context={"request": request},
    )
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)
