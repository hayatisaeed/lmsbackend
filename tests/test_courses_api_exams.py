from datetime import timedelta

import jwt
import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.courses import models as m
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
    return User.objects.create_user(phone="+10000000000")


@pytest.fixture
def course(db):
    return m.Course.objects.create(name="Math", description="desc")


@pytest.fixture
def exam(user, db):
    return m.Exam.objects.create(title="Midterm", created_by=user)


def test_publish_returns_totals_and_locks_edits(client, user, exam, course):
    m.Question.objects.create(
        exam=exam, type=m.Question.Type.TEXT, title="Q1", order_index=1
    )
    q_mcq = m.Question.objects.create(
        exam=exam, type=m.Question.Type.MCQ, title="Q2", order_index=2
    )
    m.MCQOption.objects.create(
        question=q_mcq, text="A", is_correct=True, order_index=1
    )
    m.MCQOption.objects.create(
        question=q_mcq, text="B", is_correct=False, order_index=2
    )
    res = client.post(
        f"/api/v1/courses/exams/{exam.id}/publish/",
        **auth_headers(user),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["questions_count"] == 2
    assert float(body["total_max_score"]) == 2.0
    m.Attempt.objects.create(user=user, exam=exam, course=course)
    res = client.patch(
        f"/api/v1/courses/exams/{exam.id}/",
        {"description": "new"},
        format="json",
        **auth_headers(user),
    )
    assert res.status_code == 400


def test_question_delete_blocked_after_attempt(client, user, exam, course):
    q = m.Question.objects.create(
        exam=exam, type=m.Question.Type.TEXT, title="Q1", order_index=1
    )
    client.post(
        f"/api/v1/courses/exams/{exam.id}/publish/",
        **auth_headers(user),
    )
    m.Attempt.objects.create(user=user, exam=exam, course=course)
    res = client.delete(
        f"/api/v1/courses/questions/{q.id}/",
        **auth_headers(user),
    )
    assert res.status_code == 400


def test_mcq_option_creation_rules(client, user, exam):
    q = m.Question.objects.create(
        exam=exam, type=m.Question.Type.MCQ, title="Q1", order_index=1
    )
    data = [
        {"text": "A", "is_correct": True, "order_index": 1},
        {"text": "B", "is_correct": False, "order_index": 2},
    ]
    res = client.post(
        f"/api/v1/courses/questions/{q.id}/options/",
        data,
        format="json",
        **auth_headers(user),
    )
    assert res.status_code == 201
    res = client.post(
        f"/api/v1/courses/questions/{q.id}/options/",
        {"text": "C", "is_correct": True, "order_index": 3},
        format="json",
        **auth_headers(user),
    )
    assert res.status_code == 400
    q2 = m.Question.objects.create(
        exam=exam, type=m.Question.Type.MCQ, title="Q2", order_index=2
    )
    res = client.post(
        f"/api/v1/courses/questions/{q2.id}/options/",
        {"text": "A", "is_correct": True, "order_index": 1},
        format="json",
        **auth_headers(user),
    )
    assert res.status_code == 400


@override_settings(MAX_UPLOAD_SIZE_MB=1)
def test_question_asset_upload_validations(client, user, exam):
    q = m.Question.objects.create(
        exam=exam, type=m.Question.Type.TEXT, title="Q1", order_index=1
    )
    txt = SimpleUploadedFile("a.txt", b"hi", content_type="text/plain")
    res = client.post(
        f"/api/v1/courses/questions/{q.id}/files/",
        {"file": txt},
        **auth_headers(user),
    )
    assert res.status_code == 400
    big = SimpleUploadedFile(
        "b.png", b"x" * (2 * 1024 * 1024), content_type="image/png"
    )
    res = client.post(
        f"/api/v1/courses/questions/{q.id}/files/",
        {"file": big},
        **auth_headers(user),
    )
    assert res.status_code == 413
    img = SimpleUploadedFile(
        "c.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"
    )
    res = client.post(
        f"/api/v1/courses/questions/{q.id}/files/",
        {"file": img},
        **auth_headers(user),
    )
    assert res.status_code == 201


def test_exam_assignment_create_and_list(client, user, exam, course):
    now = timezone.now()
    res = client.post(
        f"/api/v1/courses/exams/{exam.id}/assign-to-course/",
        {
            "course": str(course.id),
            "start_at": now.isoformat(),
            "end_at": (now - timedelta(hours=1)).isoformat(),
        },
        format="json",
        **auth_headers(user),
    )
    assert res.status_code == 400
    res = client.post(
        f"/api/v1/courses/exams/{exam.id}/assign-to-course/",
        {
            "course": str(course.id),
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(hours=1)).isoformat(),
            "duration_override": 10,
        },
        format="json",
        **auth_headers(user),
    )
    assert res.status_code == 201
    res = client.get(
        f"/api/v1/courses/exams/{exam.id}/assignments/",
        **auth_headers(user),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
