from datetime import timedelta

import jwt
import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
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
    return User.objects.create_user(phone="+10000000001")


@pytest.fixture
def course(db):
    return m.Course.objects.create(name="Sci", description="d")


@pytest.fixture
def exam(user, db):
    return m.Exam.objects.create(
        title="Quiz", created_by=user, auto_grade_if_all_mcq=True
    )


@pytest.fixture
def question(exam):
    return m.Question.objects.create(
        exam=exam,
        type=m.Question.Type.FILE,
        title="Upload",
        order_index=1,
        answer_accepts_file_types=m.Question.FileTypes.IMAGES_AND_PDF,
        answer_max_files=1,
    )


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


def test_answer_file_upload_and_fetch(client, user, course, exam, question, assignment):
    course.participants.add(user)
    res = client.post(
        f"/api/v1/courses/{course.id}/exams/{exam.id}/attempts/start/",
        **auth_headers(user),
    )
    attempt = m.Attempt.objects.get(id=res.json()["id"])
    answer = m.Answer.objects.create(attempt=attempt, question=question)
    upload = SimpleUploadedFile("img.png", b"1", content_type="image/png")
    res = client.post(
        "/api/v1/courses/files/upload/answer/",
        {"answer_id": str(answer.id), "file": upload},
        **auth_headers(user),
    )
    assert res.status_code == 201
    file_id = res.json()["file_id"]
    res = client.get(f"/api/v1/courses/files/{file_id}/", **auth_headers(user))
    assert res.status_code == 302


def test_answer_file_upload_invalid_type(
    client, user, course, exam, question, assignment
):
    course.participants.add(user)
    res = client.post(
        f"/api/v1/courses/{course.id}/exams/{exam.id}/attempts/start/",
        **auth_headers(user),
    )
    attempt = m.Attempt.objects.get(id=res.json()["id"])
    answer = m.Answer.objects.create(attempt=attempt, question=question)
    upload = SimpleUploadedFile("bad.txt", b"1", content_type="text/plain")
    res = client.post(
        "/api/v1/courses/files/upload/answer/",
        {"answer_id": str(answer.id), "file": upload},
        **auth_headers(user),
    )
    assert res.status_code == 400


def test_answer_file_upload_max_files(client, user, course, exam, question, assignment):
    course.participants.add(user)
    res = client.post(
        f"/api/v1/courses/{course.id}/exams/{exam.id}/attempts/start/",
        **auth_headers(user),
    )
    attempt = m.Attempt.objects.get(id=res.json()["id"])
    answer = m.Answer.objects.create(attempt=attempt, question=question)
    upload1 = SimpleUploadedFile("a.png", b"1", content_type="image/png")
    client.post(
        "/api/v1/courses/files/upload/answer/",
        {"answer_id": str(answer.id), "file": upload1},
        **auth_headers(user),
    )
    upload2 = SimpleUploadedFile("b.png", b"1", content_type="image/png")
    res = client.post(
        "/api/v1/courses/files/upload/answer/",
        {"answer_id": str(answer.id), "file": upload2},
        **auth_headers(user),
    )
    assert res.status_code == 400


def test_question_asset_upload(client, user, exam, question):
    upload = SimpleUploadedFile("q.png", b"1", content_type="image/png")
    res = client.post(
        "/api/v1/courses/files/upload/question-asset/",
        {"question_id": str(question.id), "file": upload},
        **auth_headers(user),
    )
    assert res.status_code == 201
    assert m.QuestionFile.objects.filter(question=question).exists()
