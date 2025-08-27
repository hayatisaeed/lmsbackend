import logging
from decimal import Decimal

import redis
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import connection
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Q
from .models import Course

from .models import (
    Answer,
    AnswerFile,
    Attempt,
    Exam,
    ExamAssignment,
    GraderAssignment,
    GradingItem,
    Question,
    QuestionFile,
    Course,
)
from .permissions import IsAttemptOwner, IsEnrolledInCourse, IsExamAdmin, IsGrader
from .serializers import (
    ActiveExamSerializer,
    AnswerAutoSaveSerializer,
    AttemptDetailSerializer,
    AttemptResultSerializer,
    AttemptStartSerializer,
    AttemptSubmitSerializer,
    DraftFileDeleteSerializer,
    ExamAssignmentSerializer,
    ExamSerializer,
    GraderAssignmentSerializer,
    GradingItemSerializer,
    MCQOptionSerializer,
    QuestionSerializer,
    CourseDetailSerializer,
    CourseListSerializer

)


def health(_request):
    return JsonResponse({"status": "ok"})


def readiness(_request):
    checks = {"db": False, "redis": False, "storage": False}
    try:
        connection.ensure_connection()
        checks["db"] = True
    except Exception:
        pass
    try:
        redis.Redis.from_url(settings.CELERY_BROKER_URL).ping()
        checks["redis"] = True
    except Exception:
        pass
    try:
        default_storage.exists("")
        checks["storage"] = True
    except Exception:
        pass
    ok = checks["db"] and checks["redis"]
    status = "ok" if ok else "error"
    return JsonResponse({"status": status, **checks})


class CourseListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Base query - public courses
        query = Q(visibility=Course.Visibility.PUBLIC)
        
        # If user is admin, include private courses too
        if request.user.is_staff:  # Adjust this based on your admin check
            query = query | Q(visibility=Course.Visibility.PRIVATE)
        else:
            # For non-admin users, also include private courses they've joined
            query = query | Q(visibility=Course.Visibility.PRIVATE, participants=request.user)
        
        courses = Course.objects.filter(query).distinct()
        serializer = CourseListSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        course_id = request.data.get('course_id')
        if not course_id:
            return Response(
                {'error': 'course_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = get_object_or_404(Course, id=course_id)
            
            # Check if course is free
            if course.access_mode != Course.AccessMode.FREE:
                return Response(
                    {'error': 'This course requires purchase'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add user to participants if not already joined
            if not course.participants.filter(id=request.user.id).exists():
                course.participants.add(request.user)
            
            return Response(
                {'status': 'success', 'message': 'Successfully joined the course'},
                status=status.HTTP_200_OK
            )
            
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class CourseDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user can access this course
            if (course.visibility == Course.Visibility.PRIVATE and 
                not request.user.is_staff and 
                not course.participants.filter(id=request.user.id).exists()):
                return Response(
                    {'error': 'You do not have permission to access this course'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Use different serializer for admin users
            if request.user.is_staff:
                serializer = CourseDetailSerializer(course, context={'request': request})
            else:
                serializer = CourseListSerializer(course, context={'request': request})
            
            return Response(serializer.data)
            
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(tags=["Exams"])
class ExamListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Exam.objects.filter(created_by=request.user)
        status_param = request.query_params.get("status")
        created_by = request.query_params.get("created_by")
        if status_param:
            qs = qs.filter(status=status_param)
        if created_by:
            qs = qs.filter(created_by_id=created_by)
        serializer = ExamSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Exams"])
class ExamDetailView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def get_object(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        self.check_object_permissions(request, exam)
        return exam

    def get(self, request, exam_id):
        exam = self.get_object(request, id=exam_id)
        serializer = ExamSerializer(exam)
        return Response(serializer.data)

    def patch(self, request, exam_id):
        exam = self.get_object(request, id=exam_id)
        serializer = ExamSerializer(exam, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(tags=["Exams"])
class ExamPublishView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    @extend_schema(request=None, responses=ExamSerializer)
    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        self.check_object_permissions(request, exam)
        serializer = ExamSerializer(
            exam, data={"status": Exam.Status.PUBLISHED}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        for q in exam.questions.filter(type=Question.Type.MCQ):
            if q.options.count() < 2:
                raise ValidationError("mcq_options_min_2")
        serializer.save()
        data = serializer.to_representation(exam)
        return Response(
            {
                "status": exam.status,
                "exam_id": exam.id,
                "questions_count": data["questions_count"],
                "total_max_score": data["total_max_score"],
            }
        )


@extend_schema(tags=["Questions"])
class QuestionCreateView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        self.check_object_permissions(request, exam)
        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(exam=exam)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Questions"])
class QuestionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def get_object(self, request, question_id):
        question = get_object_or_404(Question, id=question_id)
        self.check_object_permissions(request, question)
        return question

    def get(self, request, question_id):
        question = self.get_object(request, id=question_id)
        serializer = QuestionSerializer(question)
        return Response(serializer.data)

    def patch(self, request, question_id):
        question = self.get_object(request, id=question_id)
        serializer = QuestionSerializer(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, question_id):
        question = self.get_object(request, id=question_id)
        exam = question.exam
        if exam.status != Exam.Status.DRAFT or exam.attempts.exists():
            raise ValidationError("exam_locked")
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Questions"])
class MCQOptionCreateView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, question_id):
        question = get_object_or_404(Question, id=question_id)
        self.check_object_permissions(request, question)
        if question.type != Question.Type.MCQ:
            raise ValidationError("not_mcq")
        data = request.data
        options_data = data if isinstance(data, list) else [data]
        for item in options_data:
            item["question"] = str(question.id)
        if question.options.count() + len(options_data) < 2:
            raise ValidationError("min_options")
        existing_correct = question.options.filter(is_correct=True).count()
        incoming_correct = sum(1 for item in options_data if item.get("is_correct"))
        if existing_correct + incoming_correct != 1:
            raise ValidationError("exactly_one_correct")
        created = []
        for item in options_data:
            serializer = MCQOptionSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            created.append(serializer.data)
        return Response(created, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Questions"])
class QuestionFileUploadView(APIView):
    parser_classes = [MultiPartParser, JSONParser]
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, question_id):
        question = get_object_or_404(Question, id=question_id)
        self.check_object_permissions(request, question)
        if question.exam.status != Exam.Status.DRAFT or question.exam.attempts.exists():
            raise ValidationError("exam_locked")
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError("file_required")
        if not upload.content_type or not upload.content_type.startswith("image/"):
            raise ValidationError("invalid_type")
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if upload.size > max_bytes:
            return Response(status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        path = default_storage.save(upload.name, upload)
        file_url = default_storage.url(path)
        qf = QuestionFile.objects.create(
            question=question, title=upload.name, file=file_url
        )
        return Response(
            {"id": str(qf.id), "title": qf.title, "file": qf.file},
            status=status.HTTP_201_CREATED,
        )

@extend_schema(tags=["Files"])
class QuestionAssetUploadView(QuestionFileUploadView):
    def post(self, request):
        question_id = request.data.get("question_id")
        if not question_id:
            raise ValidationError("question_id_required")
        return super().post(request, question_id)


@extend_schema(tags=["Questions"])
class QuestionFileDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def delete(self, request, qf_id):
        instance = get_object_or_404(QuestionFile, id=qf_id)
        exam = instance.question.exam
        self.check_object_permissions(request, exam)
        if exam.status != Exam.Status.DRAFT or exam.attempts.exists():
            raise ValidationError("exam_locked")
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema(tags=["Files"])
class AnswerFileUploadView(APIView):
    parser_classes = [MultiPartParser, JSONParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        answer_id = request.data.get("answer_id")
        upload = request.FILES.get("file")
        if not answer_id or not upload:
            raise ValidationError("answer_id_and_file_required")
        answer = get_object_or_404(Answer, id=answer_id)
        if answer.attempt.user_id != request.user.id:
            raise PermissionDenied()
        question = answer.question
        if question.type not in [Question.Type.FILE, Question.Type.TEXT_OR_FILE]:
            raise ValidationError("question_not_file")
        if answer.files.count() >= question.answer_max_files:
            raise ValidationError("max_files_exceeded")
        ctype = upload.content_type or ""
        if not ctype.startswith("image/"):
            if not (
                ctype == "application/pdf"
                and question.answer_accepts_file_types
                == Question.FileTypes.IMAGES_AND_PDF
            ):
                raise ValidationError("invalid_type")
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if upload.size > max_bytes:
            return Response(status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        path = default_storage.save(upload.name, upload)
        file_url = default_storage.url(path)
        af = AnswerFile.objects.create(
            answer=answer, title=upload.name, file=file_url
        )
        return Response(
            {"file_id": str(af.id), "url": af.file},
            status=status.HTTP_201_CREATED,
        )

    def _storage_path(self, url: str) -> str:
        from urllib.parse import urlparse

        path = urlparse(url).path
        media_url = settings.MEDIA_URL
        if path.startswith(media_url):
            path = path[len(media_url) :]
        return path.lstrip("/")

    @extend_schema(request=DraftFileDeleteSerializer, responses={204: None})
    def delete(self, request):
        serializer = DraftFileDeleteSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        af = serializer.validated_data["answer_file"]
        storage_path = self._storage_path(af.file)
        try:
            default_storage.delete(storage_path)
        except Exception:  # pragma: no cover - ignore storage errors
            pass
        attempt = af.answer.attempt
        question_id = af.answer.question_id
        file_id = str(af.id)
        af.delete()
        logging.getLogger(__name__).info(
            "AnswerFileDeleted",
            extra={
                "attempt_id": str(attempt.id),
                "question_id": str(question_id),
                "file_id": file_id,
                "by_user": request.user.id,
            },
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema(tags=["Files"])
class FileServeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        try:
            qf = QuestionFile.objects.get(id=file_id)
            if qf.question.exam.created_by_id != request.user.id:
                raise PermissionDenied()
            return Response(status=status.HTTP_302_FOUND, headers={"Location": qf.file})
        except QuestionFile.DoesNotExist:
            af = get_object_or_404(AnswerFile, id=file_id)
            attempt = af.answer.attempt
            if (
                attempt.user_id != request.user.id
                and attempt.exam.created_by_id != request.user.id
            ):
                raise PermissionDenied() from None
            return Response(
                status=status.HTTP_302_FOUND, headers={"Location": af.file}
            )


@extend_schema(tags=["ExamAssignments"])
class ExamAssignView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        self.check_object_permissions(request, exam)
        data = request.data.copy()
        data["exam"] = str(exam_id)
        serializer = ExamAssignmentSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["ExamAssignments"])
class ExamAssignmentListView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]
    pagination_class = PageNumberPagination

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        self.check_object_permissions(request, exam)
        qs = exam.assignments.all()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ExamAssignmentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


@extend_schema(tags=["Attempts"])
class ActiveExamsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        assignments = ExamAssignment.objects.filter(
            course__participants=request.user,
            start_at__lte=now,
            end_at__gte=now,
        ).select_related("exam", "course")
        items = []
        for assignment in assignments:
            attempt = Attempt.objects.filter(
                user=request.user,
                exam=assignment.exam,
                course=assignment.course,
            ).first()
            items.append(
                {
                    "exam_id": assignment.exam_id,
                    "course_id": assignment.course_id,
                    "title": assignment.exam.title,
                    "start_at": assignment.start_at,
                    "end_at": assignment.end_at,
                    "started": bool(attempt),
                    "attempt_status": attempt.status if attempt else None,
                    "attempt_id": attempt.id if attempt else None,
                    "expires_at": attempt.expires_at if attempt else None,
                }
            )
        serializer = ActiveExamSerializer(items, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Attempts"])
class AttemptStartView(APIView):
    permission_classes = [IsAuthenticated, IsEnrolledInCourse]

    def post(self, request, course_id, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        data = {"exam": str(exam_id), "course": str(course_id)}
        serializer = AttemptStartSerializer(
            data=data, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            if "attempt_exists" in exc.detail:
                existing = Attempt.objects.get(
                    user=request.user, exam=exam, course_id=course_id
                )
                self.check_object_permissions(request, existing)
                detail = AttemptDetailSerializer(existing)
                return Response(detail.data, status=status.HTTP_409_CONFLICT)
            raise
        attempt = serializer.save()
        detail = AttemptDetailSerializer(attempt)
        return Response(detail.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Attempts"], request=AttemptDetailSerializer)
class AttemptDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAttemptOwner]

    def get(self, request, attempt_id):
        attempt = get_object_or_404(Attempt, id=attempt_id)
        self.check_object_permissions(request, attempt)
        serializer = AttemptDetailSerializer(attempt)
        return Response(serializer.data)


@extend_schema(tags=["Attempts"])
class AnswerAutosaveView(APIView):
    permission_classes = [IsAuthenticated, IsAttemptOwner]

    def put(self, request, attempt_id, question_id):
        attempt = get_object_or_404(Attempt, id=attempt_id)
        self.check_object_permissions(request, attempt)
        if timezone.now() >= attempt.expires_at:
            return Response({"detail": "attempt_expired"}, status=400)
        question = get_object_or_404(
            Question, id=question_id, exam=attempt.exam
        )
        serializer = AnswerAutoSaveSerializer(
            data=request.data,
            context={"attempt": attempt, "question": question},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


@extend_schema(tags=["Attempts"])
class AttemptSubmitView(APIView):
    permission_classes = [IsAuthenticated, IsAttemptOwner]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(Attempt, id=attempt_id)
        self.check_object_permissions(request, attempt)
        serializer = AttemptSubmitSerializer(
            data=request.data, context={"attempt": attempt}
        )
        serializer.is_valid(raise_exception=True)
        attempt = serializer.save()
        return Response(AttemptDetailSerializer(attempt).data)


@extend_schema(tags=["Attempts"])
class AttemptResultView(APIView):
    permission_classes = [IsAuthenticated, IsAttemptOwner]

    def get(self, request, attempt_id):
        attempt = get_object_or_404(Attempt, id=attempt_id)
        self.check_object_permissions(request, attempt)
        serializer = AttemptResultSerializer(attempt)
        return Response(serializer.data)


@extend_schema(tags=["Exams"])
class GraderAssignmentView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        self.check_object_permissions(request, exam)
        payload = {**request.data, "exam": exam.id}
        serializer = GraderAssignmentSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        assignment, created = GraderAssignment.objects.get_or_create(
            exam=exam,
            teacher=serializer.validated_data["teacher"],
            defaults={"scope": serializer.validated_data["scope"]},
        )
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(GraderAssignmentSerializer(assignment).data, status=status_code)


@extend_schema(tags=["Grading"])
class GradingQueueView(APIView):
    permission_classes = [IsAuthenticated, IsGrader]

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        self.check_object_permissions(request, exam)
        attempts = exam.attempts.filter(status=Attempt.Status.SUBMITTED)
        data = [
            {
                "attempt_id": str(a.id),
                "user_id": str(a.user_id),
                "status": a.status,
            }
            for a in attempts
        ]
        return Response(data)


@extend_schema(tags=["Grading"], request=GradingItemSerializer)
class GradeAnswerView(APIView):
    permission_classes = [IsAuthenticated, IsGrader]

    def post(self, request, answer_id):
        answer = get_object_or_404(Answer, id=answer_id)
        exam = answer.question.exam
        self.check_object_permissions(request, exam)
        payload = {
            **request.data,
            "answer": answer.id,
            "grader": request.user.id,
        }
        serializer = GradingItemSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        item, _ = GradingItem.objects.update_or_create(
            answer=answer,
            grader=request.user,
            defaults={
                "score_awarded": serializer.validated_data.get(
                    "score_awarded", Decimal("0.0")
                ),
                "feedback": serializer.validated_data.get("feedback", ""),
                "status": GradingItem.Status.GRADED,
                "graded_at": timezone.now(),
            },
        )
        return Response(
            {"status": item.status, "graded_at": item.graded_at},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Grading"], request=None)
class FinalizeAttemptView(APIView):
    permission_classes = [IsAuthenticated, IsGrader]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(Attempt, id=attempt_id)
        self.check_object_permissions(request, attempt.exam)
        graded_items = GradingItem.objects.filter(
            answer__attempt=attempt, status=GradingItem.Status.GRADED
        )
        if graded_items.count() < attempt.answers.count():
            raise ValidationError("Not all answers graded")
        total = (
            graded_items.aggregate(sum=Sum("score_awarded"))["sum"]
            or Decimal("0.0")
        )
        attempt.final_score = total
        attempt.is_passed = total >= attempt.exam.min_accept_score
        attempt.status = Attempt.Status.GRADED
        attempt.save(update_fields=["final_score", "is_passed", "status"])
        return Response({"final_score": str(total)})


@extend_schema(tags=["Grading"], request=None)
class ReleaseAttemptView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(Attempt, id=attempt_id)
        self.check_object_permissions(request, attempt.exam)
        if attempt.status != Attempt.Status.GRADED:
            raise ValidationError("Attempt not graded")
        attempt.status = Attempt.Status.RELEASED
        attempt.result_visibility_state = Attempt.ResultVisibility.VISIBLE
        attempt.save(update_fields=["status", "result_visibility_state"])
        return Response({"status": attempt.status})


@extend_schema(tags=["Grading"], request=None)
class BulkReleaseExamResultsView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        self.check_object_permissions(request, exam)
        updated = exam.attempts.filter(status=Attempt.Status.GRADED).update(
            status=Attempt.Status.RELEASED,
            result_visibility_state=Attempt.ResultVisibility.VISIBLE,
        )
        return Response({"released": updated})
