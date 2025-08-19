# views.py (fixed)
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
)
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone

from .models import (
    User, IdentityInformation, EducationalLevel, StudyBranch, Olympiad,
    EducationalProfile, State, City, ParentContact
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, OTPRequestSerializer, OTPVerificationSerializer,
    PasswordLoginSerializer, EducationalLevelSerializer, StudyBranchSerializer, OlympiadSerializer,
    IdentityInformationSerializer, EducationalProfileSerializer, StateSerializer, CitySerializer,
    ParentContactSerializer, ParentVerificationSerializer, ProfileCompletionSerializer
)
from .permissions import (
    IsProfileCompletePermission, IsIdentityVerifiedPermission,
    IsNotVerifiedPermission, IsAuthenticatedOrReadOnly
)
from .utils import send_otp


# ---------- AUTH ----------

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='User Registration',
        description='Register a new user with phone number (other fields optional)',
        request=UserRegistrationSerializer,
        responses={201: UserSerializer},
        examples=[
            OpenApiExample('Minimal', value={'phone': '+989123456789'}, status_codes=['201']),
            OpenApiExample('Full', value={'phone': '+989123456789','display_name':'John','email':'john@example.com','password':'secret12345'}, status_codes=['201']),
        ],
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'message': 'User registered successfully','user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Request OTP',
        description='Request OTP code to be sent to the provided phone number',
        request=OTPRequestSerializer,
        responses={200: inline_serializer(name='OTPRequestResponse', fields={
            'phone': OpenApiTypes.STR,
            'message': OpenApiTypes.STR,
        })},
        examples=[OpenApiExample('Valid', value={'phone': '+989123456789'}, status_codes=['200'])],
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Verify OTP and Login/Register',
        description='Verify OTP code and automatically create/update user, then return JWT tokens',
        request=OTPVerificationSerializer,
        responses={200: inline_serializer(name='OTPVerificationResponse', fields={
            'message': OpenApiTypes.STR,
            'access': OpenApiTypes.STR,
            'refresh': OpenApiTypes.STR,
            'user': UserSerializer(),
            'is_new_user': OpenApiTypes.BOOL,
        })},
        examples=[
            OpenApiExample('Minimal', value={'phone': '+989123456789','code': '123456'}, status_codes=['200']),
            OpenApiExample('With profile data', value={'phone': '+989123456789','code':'123456','display_name':'John','email':'john@example.com'}, status_codes=['200']),
        ],
    )
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'User authenticated successfully',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
                'is_new_user': user.created_at == user.updated_at
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UnifiedLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Unified Login/Registration',
        description='Single endpoint for both login and registration - just provide phone number',
        request=inline_serializer(name='UnifiedLoginRequest', fields={'phone': OpenApiTypes.STR}),
        responses={200: inline_serializer(name='UnifiedLoginResponse', fields={
            'message': OpenApiTypes.STR,
            'phone': OpenApiTypes.STR,
            'is_test_user': OpenApiTypes.BOOL,
            'test_info': OpenApiTypes.STR,
            'note': OpenApiTypes.STR,
        })},
        examples=[OpenApiExample('Login/Register', value={'phone': '+989123456789'}, status_codes=['200'])],
    )
    def post(self, request):
        phone = request.data.get('phone')
        if not phone:
            return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from phonenumber_field.phonenumber import to_python
            phone_number = to_python(phone, region='IR')
            if not phone_number or not phone_number.is_valid():
                return Response({'error': 'Invalid phone number format'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': 'Invalid phone number format'}, status=status.HTTP_400_BAD_REQUEST)

        from .utils import is_test_phone_number, get_test_phone_info
        is_test = is_test_phone_number(phone_number)

        try:
            send_otp(phone_number)
            response_data = {'message': 'OTP sent successfully', 'phone': str(phone_number)}
            if is_test:
                test_info = get_test_phone_info()
                response_data.update({
                    'is_test_user': True,
                    'test_info': f"🧪 Test Mode: Use OTP code {test_info['test_otp']}",
                    'note': 'This is a test phone number. No real SMS will be sent.',
                })
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestPhoneInfoView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Get Test Phone Information',
        description='Get information about the test phone number for development/testing purposes',
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        from .utils import get_test_phone_info
        test_info = get_test_phone_info()
        return Response({
            'message': 'Test phone number information',
            'test_phone': test_info['test_phone'],
            'test_otp': test_info['test_otp'],
            'description': test_info['description'],
            'usage': {
                'step1': f"POST /api/users/auth/login/ with phone: {test_info['test_phone']}",
                'step2': f"POST /api/users/auth/verify/otp/ with phone: {test_info['test_phone']} and code: {test_info['test_otp']}",
                'note': 'No real SMS will be sent for this phone number'
            }
        }, status=status.HTTP_200_OK)


class PasswordLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Login with phone and password',
        request=PasswordLoginSerializer,
        responses={200: inline_serializer(name='PasswordLoginResponse', fields={
            'access': OpenApiTypes.STR, 'refresh': OpenApiTypes.STR, 'user': UserSerializer(),
        }), 401: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            password = serializer.validated_data['password']
            user = authenticate(request, phone=phone, password=password)
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- EDUCATION ----------

@extend_schema(
    tags=['Education'], summary='List Educational Levels',
    responses={200: EducationalLevelSerializer(many=True)}
)
class EducationalLevelListView(generics.ListAPIView):
    queryset = EducationalLevel.objects.all()
    serializer_class = EducationalLevelSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


@extend_schema(
    tags=['Education'],
    summary='List Study Branches',
    description='Get study branches, optionally filtered by educational level',
    parameters=[OpenApiParameter(name='level', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY,
                                 description='Filter by educational level ID')],
    responses={200: StudyBranchSerializer(many=True)}
)
class StudyBranchListView(generics.ListAPIView):
    serializer_class = StudyBranchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        level_id = self.request.query_params.get('level')
        if level_id:
            # BUGFIX: correct FK name
            return StudyBranch.objects.filter(educational_level_id=level_id)
        return StudyBranch.objects.all()


@extend_schema(
    tags=['Education'], summary='List Olympiads',
    responses={200: OlympiadSerializer(many=True)}
)
class OlympiadListView(generics.ListAPIView):
    queryset = Olympiad.objects.filter(published=True)
    serializer_class = OlympiadSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# ---------- PROFILE STEPS ----------

class IdentityInformationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Profile'], responses={200: IdentityInformationSerializer, 404: OpenApiTypes.OBJECT})
    def get(self, request):
        try:
            identity = request.user.identityinformation
            return Response(IdentityInformationSerializer(identity).data)
        except IdentityInformation.DoesNotExist:
            return Response({'message': 'No identity information found'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(tags=['Profile'], request=IdentityInformationSerializer, responses={201: IdentityInformationSerializer, 400: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = IdentityInformationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            identity = serializer.save()
            request.user.check_profile_completion()
            return Response({'message': 'Identity information submitted successfully','identity': IdentityInformationSerializer(identity).data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EducationalProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Profile'], responses={200: EducationalProfileSerializer, 404: OpenApiTypes.OBJECT})
    def get(self, request):
        try:
            profile = request.user.educationalprofile
            return Response(EducationalProfileSerializer(profile).data)
        except EducationalProfile.DoesNotExist:
            return Response({'message': 'No educational profile found'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(tags=['Profile'], request=EducationalProfileSerializer, responses={201: EducationalProfileSerializer, 400: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = EducationalProfileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save()
            request.user.check_profile_completion()
            return Response({'message': 'Educational profile submitted successfully','profile': EducationalProfileSerializer(profile).data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParentContactView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Parent'], responses={200: ParentContactSerializer, 404: OpenApiTypes.OBJECT})
    def get(self, request):
        try:
            parent_contact = request.user.parentcontact
            return Response(ParentContactSerializer(parent_contact).data)
        except ParentContact.DoesNotExist:
            return Response({'message': 'No parent contact found'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(tags=['Parent'], request=ParentContactSerializer, responses={201: ParentContactSerializer, 400: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = ParentContactSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            parent_contact = serializer.save()
            request.user.check_profile_completion()
            return Response({'message': 'Parent contact submitted successfully. Verification code sent.','parent_contact': ParentContactSerializer(parent_contact).data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParentVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Parent'], request=ParentVerificationSerializer, responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = ParentVerificationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.check_profile_completion()
            return Response({'message': 'Parent contact verified successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileCompletionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Profile'], summary='Profile completion status', responses={200: ProfileCompletionSerializer})
    def get(self, request):
        user = request.user

        # BUGFIX: no Location model / attribute; use presence of state/city
        try:
            identity_completed = user.identityinformation.is_verified
        except IdentityInformation.DoesNotExist:
            identity_completed = False

        try:
            education_completed = bool(user.educationalprofile)
        except EducationalProfile.DoesNotExist:
            education_completed = False

        location_completed = bool(getattr(user, 'state_id', None) and getattr(user, 'city_id', None))

        try:
            parent_completed = user.parentcontact.is_verified
        except ParentContact.DoesNotExist:
            parent_completed = False

        data = {
            'is_profile_complete': user.is_profile_complete,
            'identity_completed': identity_completed,
            'education_completed': education_completed,
            'location_completed': location_completed,
            'parent_completed': parent_completed,
        }
        return Response(data, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Profile'], summary='Current user profile', responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class ProtectedResourceView(APIView):
    permission_classes = [IsProfileCompletePermission]

    @extend_schema(tags=['Profile'], summary='Protected resource (profile must be complete)', responses={200: inline_serializer(name='ProtectedResourceResponse', fields={
        'message': OpenApiTypes.STR,
        'user': UserSerializer(),
    })})
    def get(self, request):
        return Response({'message': 'Access granted to protected resource','user': UserSerializer(request.user).data}, status=status.HTTP_200_OK)


# ---------- LOCATION ----------

@extend_schema(tags=['Location'], summary='List States', responses={200: StateSerializer(many=True)})
class StateListView(generics.ListAPIView):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


@extend_schema(
    tags=['Location'],
    summary='List Cities',
    description='Get cities, optionally filtered by state',
    parameters=[OpenApiParameter(name='state', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Filter by state ID')],
    responses={200: CitySerializer(many=True)}
)
class CityListView(generics.ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        state_id = self.request.query_params.get('state')
        if state_id:
            return City.objects.filter(state_id=state_id)
        return City.objects.all()
