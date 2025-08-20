import redis
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Exam, Question, QuestionFile
from .permissions import IsExamAdmin
from .serializers import (
    ExamAssignmentSerializer,
    ExamSerializer,
    MCQOptionSerializer,
    QuestionSerializer,
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

    def get_object(self, request, pk):
        exam = get_object_or_404(Exam, pk=pk)
        self.check_object_permissions(request, exam)
        return exam

    def get(self, request, pk):
        exam = self.get_object(request, pk)
        serializer = ExamSerializer(exam)
        return Response(serializer.data)

    def patch(self, request, pk):
        exam = self.get_object(request, pk)
        serializer = ExamSerializer(exam, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(tags=["Exams"])
class ExamPublishView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    @extend_schema(request=None, responses=ExamSerializer)
    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
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
        exam = get_object_or_404(Exam, pk=exam_id)
        self.check_object_permissions(request, exam)
        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(exam=exam)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Questions"])
class QuestionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def get_object(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        self.check_object_permissions(request, question)
        return question

    def get(self, request, pk):
        question = self.get_object(request, pk)
        serializer = QuestionSerializer(question)
        return Response(serializer.data)

    def patch(self, request, pk):
        question = self.get_object(request, pk)
        serializer = QuestionSerializer(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        question = self.get_object(request, pk)
        exam = question.exam
        if exam.status != Exam.Status.DRAFT or exam.attempts.exists():
            raise ValidationError("exam_locked")
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Questions"])
class MCQOptionCreateView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, question_id):
        question = get_object_or_404(Question, pk=question_id)
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
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, question_id):
        question = get_object_or_404(Question, pk=question_id)
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


@extend_schema(tags=["Questions"])
class QuestionFileDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def delete(self, request, pk):
        instance = get_object_or_404(QuestionFile, pk=pk)
        exam = instance.question.exam
        self.check_object_permissions(request, exam)
        if exam.status != Exam.Status.DRAFT or exam.attempts.exists():
            raise ValidationError("exam_locked")
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["ExamAssignments"])
class ExamAssignView(APIView):
    permission_classes = [IsAuthenticated, IsExamAdmin]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
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
        exam = get_object_or_404(Exam, pk=exam_id)
        self.check_object_permissions(request, exam)
        qs = exam.assignments.all()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ExamAssignmentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
