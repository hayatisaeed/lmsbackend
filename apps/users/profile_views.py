from drf_spectacular.utils import OpenApiResponse, extend_schema
from prometheus_client import Counter, Histogram
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.files.images import get_image_dimensions
from django.conf import settings

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


@extend_schema(tags=["Profile"])
class IdentityView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=IdentitySerializer,
        responses={
            200: IdentitySerializer,
            400: OpenApiResponse(description="Validation error"),
            429: OpenApiResponse(description="Too many requests"),
            502: OpenApiResponse(description="Identity provider error"),
        },
    )
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


class UserAvatarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def validate_avatar(self, image):
        if image.size > settings.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError("File size too large. Max 5MB allowed.")
        
        if image.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError("Unsupported file type. Use JPEG, PNG, GIF, or WEBP.")
        
        width, height = get_image_dimensions(image)
        if width < 100 or height < 100:
            raise serializers.ValidationError("Image too small. Minimum 100x100 pixels.")
        if width > 2000 or height > 2000:
            raise serializers.ValidationError("Image too large. Maximum 2000x2000 pixels.")
        
        return image

    def post(self, request):
        if 'avatar' not in request.FILES:
            return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        avatar_file = request.FILES['avatar']
        
        try:
            self.validate_avatar(avatar_file)
        except serializers.ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete old avatar if exists
        if request.user.avatar:
            request.user.avatar.delete()
        
        # Save new avatar
        request.user.avatar = avatar_file
        request.user.save()
        
        return Response({
            'status': 'success',
            'avatar_url': request.user.avatar.url
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        if request.user.avatar:
            request.user.avatar.delete()
            request.user.avatar = None
            request.user.save()
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


@extend_schema(tags=["Profile"])
class EducationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=EducationSerializer,
        responses={
            200: EducationSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        return self._handle_education_request(request, is_partial=False)

    @extend_schema(
        request=EducationSerializer,
        responses={
            200: EducationSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def put(self, request):
        return self._handle_education_request(request, is_partial=True)

    @extend_schema(
        request=EducationSerializer,
        responses={
            200: EducationSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def patch(self, request):
        return self._handle_education_request(request, is_partial=True)

    def _handle_education_request(self, request, is_partial=False):
        # Handle education data
        education_serializer = EducationSerializer(
            data=request.data, 
            context={"request": request},
            partial=is_partial
        )
        
        # Handle location data if provided
        location_data = {}
        location_fields = ["province_id", "city_id", "province", "city"]
        
        for field in location_fields:
            if field in request.data:
                location_data[field] = request.data.get(field)
        
        location_serializer = None
        if location_data:
            location_serializer = LocationSerializer(
                data=location_data, 
                context={"request": request}
            )
            location_is_valid = location_serializer.is_valid()
        else:
            location_is_valid = True
        
        education_is_valid = education_serializer.is_valid()
        
        if education_is_valid and location_is_valid:
            # Save education data
            education_result = education_serializer.save()
            
            # Save location data if provided
            location_result = None
            if location_serializer:
                location_result = location_serializer.save()
            
            response_data = {"ok": True}
            if location_result:
                response_data["location_updated"] = True
            
            return Response(response_data)
        
        # Combine errors
        errors = {}
        if not education_is_valid:
            errors.update(education_serializer.errors)
        if location_serializer and not location_is_valid:
            errors.update(location_serializer.errors)
        
        return Response({"error": errors}, status=400)


@extend_schema(tags=["Profile"])
class LocationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LocationSerializer,
        responses={
            200: LocationSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        serializer = LocationSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            return Response(serializer.save())
        return Response({"error": serializer.errors}, status=400)  # pragma: no cover


@extend_schema(tags=["Profile"])
class ParentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ParentSerializer,
        responses={
            200: ParentSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        serializer = ParentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            parent_otp_send_total.inc()
            return Response(serializer.save())
        return Response({"error": serializer.errors}, status=400)  # pragma: no cover


@extend_schema(tags=["Profile"])
class ParentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ParentVerifySerializer,
        responses={
            200: ParentVerifySerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
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


@extend_schema(tags=["Profile"])
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description="User profile data")}
    )
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
                "grade": edu.grade_id,
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


@extend_schema(tags=["Profile"])
class ProfileCompletionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Profile completion data")
        }
    )
    def get(self, request):
        return Response(request.user.profile_completion)
