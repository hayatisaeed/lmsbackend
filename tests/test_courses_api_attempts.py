from datetime import timedelta

import jwt
import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.courses import models as m
from apps.courses import tasks
from apps.users.models import User


def auth_headers(user: User) -> dict[str, str]:
    payload = {
        "sub": str(user.id),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    token = jwt.encode(payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALG)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(phone="+10000000001")


@pytest.fixture
def course(db):
    return m.Course.objects.create(name="Sci", description="d")


@pytest.fixture
def exam(user, db):
    return m.Exam.objects.create(
        title="Quiz",
        created_by=user,
        auto_grade_if_all_mcq=True,
    )


@pytest.fixture
def question(exam):
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
    return q


@pytest.fixture
def assignment(exam, course):
    start = timezone.now() - timedelta(minutes=1)
    end = timezone.now() + timedelta(minutes=30)
    return m.ExamAssignment.objects.create(
        exam=exam,
        course=course,
        start_at=start,
        end_at=end,
        duration_override=20,
    )


def test_attempt_flow(client, user, course, exam, question, assignment):
    course.participants.add(user)
    # active exams listing before start
    res = client.get("/api/v1/courses/my/active-exams/", **auth_headers(user))
    assert res.status_code == 200
    assert res.json()[0]["started"] is False

    # start attempt
    res = client.post(
        f"/api/v1/courses/{course.id}/exams/{exam.id}/attempts/start/",
        **auth_headers(user),
    )
    assert res.status_code == 201
    attempt_id = res.json()["id"]

    # active exams listing after start
    res = client.get("/api/v1/courses/my/active-exams/", **auth_headers(user))
    assert res.json()[0]["started"] is True

    # autosave answer
    option = question.options.first()
    res = client.put(
        f"/api/v1/courses/exams/attempts/{attempt_id}/answers/{question.id}/autosave/",
        {"payload": [str(option.id)]},
        format="json",
        **auth_headers(user),
    )
    assert res.status_code == 200

    # submit attempt
    res = client.post(
        f"/api/v1/courses/exams/attempts/{attempt_id}/submit/",
        **auth_headers(user),
    )
    assert res.status_code == 200
    attempt = m.Attempt.objects.get(id=attempt_id)
    assert attempt.status == m.Attempt.Status.GRADED

    # view result
    res = client.get(
        f"/api/v1/courses/exams/attempts/{attempt_id}/result/",
        **auth_headers(user),
    )
    body = res.json()
    assert "final_score" in body


def test_autosubmit_task(user, course, exam, question, assignment):
    course.participants.add(user)
    attempt = m.Attempt.objects.create(
        user=user,
        exam=exam,
        course=course,
        status=m.Attempt.Status.IN_PROGRESS,
        started_at=timezone.now() - timedelta(minutes=40),
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    m.Answer.objects.create(
        attempt=attempt,
        question=question,
        final_payload=[str(question.options.first().id)],
    )
    tasks.autosubmit_expired_attempts.run()
    attempt.refresh_from_db()
    assert attempt.status == m.Attempt.Status.EXPIRED
