import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.courses import models as m
from apps.users.models import User


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(phone="+10000000000")


@pytest.fixture
def course(db):
    return m.Course.objects.create(name="Math", description="desc")


@pytest.fixture
def exam(user, db):
    return m.Exam.objects.create(title="Final", created_by=user)


def test_question_mcq_options(exam):
    q = m.Question.objects.create(
        exam=exam,
        type=m.Question.Type.MCQ,
        title="Q1",
        order_index=1,
    )
    m.MCQOption.objects.create(
        question=q, text="A", is_correct=True, order_index=1
    )
    m.MCQOption.objects.create(
        question=q, text="B", is_correct=False, order_index=2
    )
    assert q.options.count() == 2
    assert list(q.options.values_list("order_index", flat=True)) == [1, 2]
    assert q.options.filter(is_correct=True).count() == 1


def test_attempt_unique_constraint(user, exam, course):
    m.Attempt.objects.create(user=user, exam=exam, course=course)
    with pytest.raises(IntegrityError):
        m.Attempt.objects.create(user=user, exam=exam, course=course)


def test_exam_assignment_unique(course, exam):
    m.ExamAssignment.objects.create(
        exam=exam,
        course=course,
        start_at=timezone.now(),
        end_at=timezone.now(),
    )
    with pytest.raises(IntegrityError):
        m.ExamAssignment.objects.create(
            exam=exam,
            course=course,
            start_at=timezone.now(),
            end_at=timezone.now(),
        )


def test_attempt_status_enum():
    assert m.Attempt.Status.RELEASED == "released"
