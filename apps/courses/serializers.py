from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .models import (
    Answer,
    AnswerFile,
    Attempt,
    Exam,
    ExamAssignment,
    GraderAssignment,
    GradingItem,
    MCQOption,
    Question,
    QuestionFile,
)


class ExamSerializer(serializers.ModelSerializer):
    questions_count = serializers.IntegerField(read_only=True)
    total_max_score = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "description",
            "status",
            "default_correct_score",
            "default_wrong_score",
            "allow_negative_scoring",
            "duration_minutes",
            "attempt_limit",
            "auto_grade_if_all_mcq",
            "min_accept_score",
            "total_score",
            "accept_even_below_min",
            "show_score_if_passed",
            "show_score_if_failed",
            "hide_autograded_until_release",
            "created_by",
            "questions_count",
            "total_max_score",
        ]
        read_only_fields = ["created_by", "questions_count", "total_max_score"]

    def validate(self, attrs):
        instance = self.instance
        new_status = attrs.get(
            "status", instance.status if instance else Exam.Status.DRAFT
        )
        if instance:
            if instance.status == Exam.Status.PUBLISHED and instance.attempts.exists():
                if attrs.keys() - {"status"}:
                    raise serializers.ValidationError("exam_locked")
                if new_status != Exam.Status.ARCHIVED:
                    raise serializers.ValidationError("exam_locked")
            allowed = {
                Exam.Status.DRAFT: {Exam.Status.DRAFT, Exam.Status.PUBLISHED},
                Exam.Status.PUBLISHED: {Exam.Status.PUBLISHED, Exam.Status.ARCHIVED},
                Exam.Status.ARCHIVED: {Exam.Status.ARCHIVED},
            }
            if new_status not in allowed[instance.status]:
                raise serializers.ValidationError({"status": "invalid_transition"})
        allow_neg = attrs.get(
            "allow_negative_scoring",
            instance.allow_negative_scoring if instance else False,
        )
        wrong = attrs.get("default_wrong_score")
        if wrong is not None and wrong < 0 and not allow_neg:
            raise serializers.ValidationError(
                {"default_wrong_score": "negative_not_allowed"}
            )
        min_score = attrs.get("min_accept_score")
        if min_score is not None and min_score < 0:
            raise serializers.ValidationError({"min_accept_score": "must_be_positive"})
        total = attrs.get("total_score")
        if total is not None and total < 0:
            raise serializers.ValidationError({"total_score": "must_be_positive"})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["questions_count"] = instance.questions.count()
        total = Decimal("0")
        for q in instance.questions.all():
            total += q.correct_score or instance.default_correct_score
        data["total_max_score"] = total
        return data


class ExamAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamAssignment
        fields = [
            "id",
            "exam",
            "course",
            "start_at",
            "end_at",
            "duration_override",
            "reuse_last_user_result",
            "created_at",
        ]
        read_only_fields = ["created_at"]
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ExamAssignment.objects.all(),
                fields=("exam", "course"),
            )
        ]

    def validate(self, attrs):
        if attrs["start_at"] >= attrs["end_at"]:
            raise serializers.ValidationError("invalid_window")
        duration_override = attrs.get("duration_override")
        if duration_override is not None and duration_override <= 0:
            raise serializers.ValidationError(
                {"duration_override": "must_be_positive"}
            )
        return attrs


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = "__all__"

    def validate(self, attrs):
        exam = attrs.get("exam") or self.instance.exam
        if (
            exam.status == Exam.Status.PUBLISHED
            and exam.attempts.exists()
        ):
            raise serializers.ValidationError("exam_locked")
        q_type = attrs.get("type", self.instance.type if self.instance else None)
        answer_max_files = attrs.get(
            "answer_max_files",
            self.instance.answer_max_files if self.instance else 1,
        )
        accepts_files = q_type in [Question.Type.FILE, Question.Type.TEXT_OR_FILE]
        if accepts_files:
            if answer_max_files < 1:
                raise serializers.ValidationError(
                    {"answer_max_files": "min_1"}
                )
        else:
            if (
                attrs.get("answer_accepts_file_types")
                or answer_max_files != 1
            ):
                raise serializers.ValidationError("files_not_allowed")
        allow_neg = exam.allow_negative_scoring
        wrong = attrs.get("wrong_score")
        if wrong is not None and wrong < 0 and not allow_neg:
            raise serializers.ValidationError(
                {"wrong_score": "negative_not_allowed"}
            )
        correct = attrs.get("correct_score")
        if correct is not None and correct < 0:
            raise serializers.ValidationError(
                {"correct_score": "must_be_positive"}
            )
        return attrs


class MCQOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCQOption
        fields = "__all__"

    def validate(self, attrs):
        question = attrs.get("question") or self.instance.question
        is_correct = attrs.get(
            "is_correct", self.instance.is_correct if self.instance else False
        )
        existing_correct = question.options.filter(is_correct=True)
        if self.instance:
            existing_correct = existing_correct.exclude(pk=self.instance.pk)
        count = existing_correct.count()
        if is_correct:
            count += 1
        if count != 1:
            raise serializers.ValidationError("exactly_one_correct")
        return attrs


class QuestionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionFile
        fields = ["id", "title", "file"]


class MCQOptionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCQOption
        fields = ["id", "text", "order_index"]


class QuestionReadSerializer(serializers.ModelSerializer):
    options = MCQOptionReadSerializer(many=True, read_only=True)
    assets = QuestionFileSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "type",
            "title",
            "body_richtext",
            "order_index",
            "is_required",
            "options",
            "assets",
        ]


class AttemptStartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attempt
        fields = ["id", "exam", "course", "started_at", "expires_at"]
        read_only_fields = ["id", "started_at", "expires_at"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        exam: Exam = attrs["exam"]
        course = attrs["course"]
        if not course.participants.filter(id=user.id).exists():
            raise PermissionDenied("You are not enrolled in this course")
        now = timezone.now()
        try:
            assignment = ExamAssignment.objects.get(exam=exam, course=course)
        except ExamAssignment.DoesNotExist:
            raise serializers.ValidationError("assignment_missing") from None
        if not (assignment.start_at <= now <= assignment.end_at):
            raise PermissionDenied("outside_window")
        duration = assignment.duration_override or exam.duration_minutes
        if not duration:
            raise serializers.ValidationError("missing_duration")
        if Attempt.objects.filter(user=user, exam=exam, course=course).exists():
            raise serializers.ValidationError("attempt_exists")
        attrs["user"] = user
        attrs["status"] = Attempt.Status.IN_PROGRESS
        attrs["started_at"] = now
        attrs["expires_at"] = now + timedelta(minutes=duration)
        return attrs

    def create(self, validated_data):
        attempt = Attempt.objects.create(**validated_data)
        for question in attempt.exam.questions.all():
            Answer.objects.create(attempt=attempt, question=question)
        return attempt


class ActiveExamSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField()
    course_id = serializers.UUIDField()
    title = serializers.CharField()
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    started = serializers.BooleanField()
    attempt_status = serializers.CharField(allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)


class AttemptDetailSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    remaining_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = [
            "id",
            "exam",
            "course",
            "status",
            "started_at",
            "expires_at",
            "remaining_seconds",
            "questions",
        ]
        read_only_fields = fields

    def get_questions(self, obj):
        qs = obj.exam.questions.prefetch_related("options", "assets")
        return QuestionReadSerializer(qs, many=True).data

    def get_remaining_seconds(self, obj):
        if obj.expires_at:
            delta = obj.expires_at - timezone.now()
            return max(0, int(delta.total_seconds()))
        return None


class AnswerAutoSaveSerializer(serializers.Serializer):
    payload = serializers.JSONField()

    def validate(self, attrs):
        question: Question = self.context["question"]
        payload = attrs["payload"]
        if question.type == Question.Type.MCQ:
            if not isinstance(payload, list):
                raise serializers.ValidationError("invalid_payload")
            option_ids = {str(opt.id) for opt in question.options.all()}
            if not payload or any(str(p) not in option_ids for p in payload):
                raise serializers.ValidationError("invalid_option")
        elif question.type in [Question.Type.TEXT, Question.Type.TEXT_OR_FILE]:
            if not isinstance(payload, str):
                raise serializers.ValidationError("invalid_payload")
        elif question.type == Question.Type.FILE:
            raise serializers.ValidationError("files_not_supported")
        return attrs

    def save(self):
        attempt: Attempt = self.context["attempt"]
        question: Question = self.context["question"]
        answer, _ = Answer.objects.get_or_create(attempt=attempt, question=question)
        answer.final_payload = self.validated_data["payload"]
        answer.save()
        now = timezone.now().isoformat()
        return {"version": now, "saved_at": now}


class AttemptSubmitSerializer(serializers.Serializer):
    def validate(self, attrs):
        attempt: Attempt = self.context["attempt"]
        if attempt.status != Attempt.Status.IN_PROGRESS:
            raise serializers.ValidationError("invalid_status")
        for question in attempt.exam.questions.filter(is_required=True):
            ans = attempt.answers.filter(question=question).first()
            if not ans or ans.final_payload in [None, "", [], {}]:
                raise serializers.ValidationError("missing_answers")
        return attrs

    def save(self):
        attempt: Attempt = self.context["attempt"]
        now = timezone.now()
        expired = attempt.expires_at and now >= attempt.expires_at
        attempt.submitted_at = now
        attempt.status = Attempt.Status.EXPIRED if expired else Attempt.Status.SUBMITTED
        attempt.save()
        exam = attempt.exam
        if (
            exam.auto_grade_if_all_mcq
            and exam.questions.filter(type=Question.Type.MCQ).count()
            == exam.questions.count()
        ):
            score = Decimal("0")
            for question in exam.questions.all():
                answer = attempt.answers.get(question=question)
                correct = question.options.get(is_correct=True)
                chosen = answer.final_payload
                if isinstance(chosen, list):
                    chosen = chosen[0] if chosen else None
                if str(chosen) == str(correct.id):
                    score += question.correct_score or exam.default_correct_score
                else:
                    score += question.wrong_score or exam.default_wrong_score
            attempt.final_score = score
            attempt.is_passed = score >= (exam.min_accept_score or 0)
            attempt.autograded = True
            if not expired:
                attempt.status = Attempt.Status.GRADED
            attempt.result_visibility_state = (
                Attempt.ResultVisibility.PENDING
                if exam.hide_autograded_until_release
                else Attempt.ResultVisibility.VISIBLE
            )
            attempt.save()
        return attempt


class AttemptResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attempt
        fields = [
            "id",
            "status",
            "final_score",
            "is_passed",
            "result_visibility_state",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.result_visibility_state != Attempt.ResultVisibility.VISIBLE:
            data.pop("final_score", None)
            data.pop("is_passed", None)
        return data


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"


class AnswerFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerFile
        fields = "__all__"


class GradingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingItem
        fields = "__all__"


class GraderAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraderAssignment
        fields = "__all__"
