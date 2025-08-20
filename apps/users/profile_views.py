from prometheus_client import Counter, Histogram
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    EducationalProfile,
    IdentityInfo,
    Location,
    ParentContact,
)
from .serializers import (
    EducationSerializer,
    IdentitySerializer,
    LocationSerializer,
    ParentSerializer,
    ParentVerifySerializer,
)

identity_submit_total = Counter(  # pragma: no cover
    "identity_submit_total", "identity submits", ["status"]
)
identity_provider_latency_ms = Histogram(  # pragma: no cover
    "identity_provider_latency_ms", "latency", buckets=(0.1, 0.5, 1, 2, 5)
)
education_validation_errors_total = Counter(  # pragma: no cover
    "education_validation_errors_total", "education validation errors", ["field"]
)
parent_otp_send_total = Counter(
    "parent_otp_send_total", "parent otp sent"
)  # pragma: no cover
parent_otp_verify_total = Counter(  # pragma: no cover
    "parent_otp_verify_total", "parent otp verify", ["status"]
)
profile_completed_total = Counter(
    "profile_completed_total", "profiles completed"
)  # pragma: no cover


class IdentityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IdentitySerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():  # pragma: no cover
            identity_submit_total.labels(status="error").inc()  # pragma: no cover
            status_code = 400  # pragma: no cover
            if serializer.errors.get("non_field_errors") == [
                "identity_rate_limited"
            ]:  # pragma: no cover
                status_code = 429  # pragma: no cover
            return Response(
                {"error": serializer.errors}, status=status_code
            )  # pragma: no cover
        import time

        start = time.time()
        try:
            data = serializer.save()
            identity_submit_total.labels(status="success").inc()
            return Response(data)
        except serializers.ValidationError as exc:  # type: ignore[name-defined]  # pragma: no cover
            identity_submit_total.labels(status="error").inc()  # pragma: no cover
            if str(exc.detail) == "identity_provider_error":  # pragma: no cover
                return Response(
                    {"error": "identity_provider_error"}, status=502
                )  # pragma: no cover
            return Response({"error": exc.detail}, status=400)  # pragma: no cover
        finally:
            identity_provider_latency_ms.observe((time.time() - start))


class EducationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EducationSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            return Response(serializer.save())
        for field in serializer.errors.keys():  # pragma: no cover
            education_validation_errors_total.labels(
                field=field
            ).inc()  # pragma: no cover
        return Response({"error": serializer.errors}, status=400)  # pragma: no cover


class LocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LocationSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            return Response(serializer.save())
        return Response({"error": serializer.errors}, status=400)  # pragma: no cover


class ParentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ParentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            parent_otp_send_total.inc()
            return Response(serializer.save())
        return Response({"error": serializer.errors}, status=400)  # pragma: no cover


class ParentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ParentVerifySerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            parent_otp_verify_total.labels(status="success").inc()
            data = serializer.save()
            user = request.user
            if user.profile_completion["percent_complete"] == 100:
                profile_completed_total.inc()
            return Response(data)
        parent_otp_verify_total.labels(status="error").inc()  # pragma: no cover
        return Response({"error": serializer.errors}, status=400)  # pragma: no cover


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = {}
        try:
            info = IdentityInfo.objects.get(user=user)
            profile["identity"] = {
                "first_name": info.first_name,
                "last_name": info.last_name,
                "father_name": info.father_name,
                "gender": info.gender,
                "verified": info.verified,
            }
            profile["parent"] = {
                "required": info.requires_parent,
                "verified": False,
            }
        except IdentityInfo.DoesNotExist:  # pragma: no cover
            profile["identity"] = {"verified": False}
            profile["parent"] = {"required": False, "verified": False}
        try:
            contact = ParentContact.objects.get(user=user)
            profile["parent"]["verified"] = contact.verified
        except ParentContact.DoesNotExist:  # pragma: no cover
            pass
        try:
            edu = user.educationalprofile
            profile["education"] = {
                "level": edu.level_id,
                "grade": edu.grade,
                "study_branch": edu.study_branch_id,
                "olympiad_count": edu.olympiads.count(),
            }
        except EducationalProfile.DoesNotExist:  # pragma: no cover
            profile["education"] = {}
        try:
            loc = user.location
            profile["location"] = {
                "province": loc.province.name,
                "city": loc.city.name,
            }
        except Location.DoesNotExist:  # pragma: no cover
            profile["location"] = {}
        profile["percent_complete"] = request.user.profile_completion[
            "percent_complete"
        ]
        return Response(profile)


class ProfileCompletionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(request.user.profile_completion)
