from datetime import timedelta
from decimal import Decimal

import jwt
import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

import apps.courses.models as m
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
def admin(db) -> User:
    return User.objects.create_user(phone="+19990000001")


@pytest.fixture
def grader(db) -> User:
    return User.objects.create_user(phone="+19990000002")


@pytest.fixture
def student1(db) -> User:
    return User.objects.create_user(phone="+19990000003")


@pytest.fixture
def student2(db) -> User:
    return User.objects.create_user(phone="+19990000004")


@pytest.fixture
def course(db):
    return m.Course.objects.create(name="Sci", description="d")


@pytest.fixture
def exam(admin):
    return m.Exam.objects.create(
        title="Essay",
        created_by=admin,
        auto_grade_if_all_mcq=False,
        min_accept_score=5,
    )


@pytest.fixture
def question(exam):
    return m.Question.objects.create(
        exam=exam,
        type=m.Question.Type.TEXT,
        title="Q1",
        order_index=1,
        correct_score=5,
    )


@pytest.fixture
def assignment(exam, course):
    start = timezone.now() - timedelta(days=1)
    end = timezone.now() + timedelta(days=1)
    return m.ExamAssignment.objects.create(
        exam=exam, course=course, start_at=start, end_at=end
    )


def test_grading_flow(
    client,
    admin,
    grader,
    student1,
    student2,
    course,
    exam,
    question,
    assignment,
):
    # assign grader
    res = client.post(
        f"/api/v1/courses/exams/{exam.id}/graders/assign/",
        {"teacher": str(grader.id), "scope": "entire_exam"},
        format="json",
        **auth_headers(admin),
    )
    assert res.status_code in (200, 201)

    # create attempts and answers
    attempt1 = m.Attempt.objects.create(
        user=student1,
        exam=exam,
        course=course,
        status=m.Attempt.Status.SUBMITTED,
    )
    answer1 = m.Answer.objects.create(
        attempt=attempt1,
        question=question,
        final_payload={"text": "ans"},
        submitted_at=timezone.now(),
    )
    attempt2 = m.Attempt.objects.create(
        user=student2,
        exam=exam,
        course=course,
        status=m.Attempt.Status.SUBMITTED,
    )
    answer2 = m.Answer.objects.create(
        attempt=attempt2,
        question=question,
        final_payload={"text": "ans2"},
        submitted_at=timezone.now(),
    )

    # grading queue
    res = client.get(
        f"/api/v1/courses/exams/{exam.id}/grading-queue/",
        **auth_headers(grader),
    )
    assert res.status_code == 200
    body = res.json()
    assert {item["attempt_id"] for item in body} == {str(attempt1.id), str(attempt2.id)}

    # grade answers
    for ans in (answer1, answer2):
        res = client.post(
            f"/api/v1/courses/answers/{ans.id}/grade/",
            {"score_awarded": 5, "feedback": "ok"},
            format="json",
            **auth_headers(grader),
        )
        assert res.status_code == 200

    # finalize attempts
    for att in (attempt1, attempt2):
        res = client.post(
            f"/api/v1/courses/attempts/{att.id}/finalize/",
            **auth_headers(grader),
        )
        assert res.status_code == 200

    attempt1.refresh_from_db()
    assert attempt1.status == m.Attempt.Status.GRADED
    assert attempt1.final_score == Decimal("5")

    # release attempt1 individually
    res = client.post(
        f"/api/v1/courses/attempts/{attempt1.id}/release/",
        **auth_headers(admin),
    )
    assert res.status_code == 200
    attempt1.refresh_from_db()
    assert attempt1.status == m.Attempt.Status.RELEASED

    # bulk release for exam (should release attempt2)
    res = client.post(
        f"/api/v1/courses/exams/{exam.id}/results/release-bulk/",
        **auth_headers(admin),
    )
    assert res.status_code == 200
    attempt2.refresh_from_db()
    assert attempt2.status == m.Attempt.Status.RELEASED
