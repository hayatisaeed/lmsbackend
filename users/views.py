from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from django.db import transaction

from .models import (
    User, IdentityInformation, EducationalLevel, StudyBranch, Olympiad,
    EducationalProfile, State, City, ParentContact, OTPCode
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


@extend_schema(
    tags=['Authentication'],
    summary='User Registration',
    description='Register a new user with phone number (other fields optional)',
    examples=[
        OpenApiExample(
            'Minimal Registration',
            value={
                'phone': '+989123456789'
            },
            status_codes=['201']
        ),
        OpenApiExample(
            'Full Registration',
            value={
                'phone': '+989123456789',
                'display_name': 'John Doe',
                'email': 'john@example.com',
                'password': 'securepassword123'
            },
            status_codes=['201']
        )
    ]
)
class UserRegistrationView(APIView):
    """User registration with phone number (other fields optional)"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Request OTP',
    description='Request OTP code to be sent to the provided phone number',
    examples=[
        OpenApiExample(
            'Valid OTP Request',
            value={'phone': '+989123456789'},
            status_codes=['200']
        )
    ]
)
class OTPRequestView(APIView):
    """Request OTP for phone number"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Verify OTP and Login/Register',
    description='Verify OTP code and automatically create/update user, then return JWT tokens',
    examples=[
        OpenApiExample(
            'Minimal Login',
            value={
                'phone': '+989123456789',
                'code': '123456'
            },
            status_codes=['200']
        ),
        OpenApiExample(
            'Login with Profile Update',
            value={
                'phone': '+989123456789',
                'code': '123456',
                'display_name': 'John Doe',
                'email': 'john@example.com',
                'password': 'securepassword123'
            },
            status_codes=['200']
        )
    ]
)
class OTPVerificationView(APIView):
    """Verify OTP and automatically create/update user, then return JWT tokens"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            # Create or update user
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'User authenticated successfully',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
                'is_new_user': user.created_at == user.updated_at
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Unified Login/Registration',
    description='Single endpoint for both login and registration - just provide phone number',
    examples=[
        OpenApiExample(
            'Login/Register',
            value={
                'phone': '+989123456789'
            },
            status_codes=['200']
        )
    ]
)
class UnifiedLoginView(APIView):
    """Unified login/registration endpoint - just provide phone number"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        phone = request.data.get('phone')
        if not phone:
            return Response({
                'error': 'Phone number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate phone number
        try:
            from phonenumber_field.phonenumber import to_python
            phone_number = to_python(phone, region='IR')
            if not phone_number or not phone_number.is_valid():
                return Response({
                    'error': 'Invalid phone number format'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({
                'error': 'Invalid phone number format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if this is a test phone number
        from .utils import is_test_phone_number, get_test_phone_info
        is_test = is_test_phone_number(phone_number)
        
        # Send OTP
        try:
            otp_code = send_otp(phone_number)
            
            response_data = {
                'message': 'OTP sent successfully',
                'phone': str(phone_number)
            }
            
            # Add test information if it's a test phone number
            if is_test:
                test_info = get_test_phone_info()
                response_data.update({
                    'is_test_user': True,
                    'test_info': f"🧪 Test Mode: Use OTP code {test_info['test_otp']} for verification",
                    'note': 'This is a test phone number. No real SMS will be sent.'
                })
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to send OTP'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Authentication'],
    summary='Get Test Phone Information',
    description='Get information about the test phone number for development/testing purposes'
)
class TestPhoneInfoView(APIView):
    """Get information about test phone number for development"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        from .utils import get_test_phone_info
        test_info = get_test_phone_info()
        
        return Response({
            'message': 'Test phone number information',
            'test_phone': test_info['test_phone'],
            'test_otp': test_info['test_otp'],
            'description': test_info['description'],
            'usage': {
                'step1': f"POST /api/auth/login/ with phone: {test_info['test_phone']}",
                'step2': f"POST /api/auth/verify/otp/ with phone: {test_info['test_phone']} and code: {test_info['test_otp']}",
                'note': 'No real SMS will be sent for this phone number'
            }
        }, status=status.HTTP_200_OK)


class PasswordLoginView(APIView):
    """Login with phone and password"""
    permission_classes = [AllowAny]
    
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
            else:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Education'],
    summary='List Educational Levels',
    description='Get all available educational levels'
)
class EducationalLevelListView(generics.ListAPIView):
    """List all educational levels"""
    queryset = EducationalLevel.objects.all()
    serializer_class = EducationalLevelSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


@extend_schema(
    tags=['Education'],
    summary='List Study Branches',
    description='Get study branches, optionally filtered by educational level',
    parameters=[
        OpenApiParameter(
            name='level',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by educational level ID'
        )
    ]
)
class StudyBranchListView(generics.ListAPIView):
    """List study branches for a specific level"""
    serializer_class = StudyBranchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        level_id = self.request.query_params.get('level', None)
        if level_id:
            return StudyBranch.objects.filter(level_id=level_id)
        return StudyBranch.objects.all()


@extend_schema(
    tags=['Education'],
    summary='List Olympiads',
    description='Get all published olympiads'
)
class OlympiadListView(generics.ListAPIView):
    """List all published olympiads"""
    queryset = Olympiad.objects.filter(published=True)
    serializer_class = OlympiadSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class IdentityInformationView(APIView):
    """Handle identity information submission"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            identity = request.user.identityinformation
            serializer = IdentityInformationSerializer(identity)
            return Response(serializer.data)
        except IdentityInformation.DoesNotExist:
            return Response({'message': 'No identity information found'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        serializer = IdentityInformationSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            identity = serializer.save()
            
            # Update user's profile completion status
            request.user.check_profile_completion()
            
            return Response({
                'message': 'Identity information submitted successfully',
                'identity': IdentityInformationSerializer(identity).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EducationalProfileView(APIView):
    """Handle educational profile submission"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = request.user.educationalprofile
            serializer = EducationalProfileSerializer(profile)
            return Response(serializer.data)
        except EducationalProfile.DoesNotExist:
            return Response({'message': 'No educational profile found'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        serializer = EducationalProfileSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            profile = serializer.save()
            
            # Update user's profile completion status
            request.user.check_profile_completion()
            
            return Response({
                'message': 'Educational profile submitted successfully',
                'profile': EducationalProfileSerializer(profile).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParentContactView(APIView):
    """Handle parent contact information submission"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            parent_contact = request.user.parentcontact
            serializer = ParentContactSerializer(parent_contact)
            return Response(serializer.data)
        except ParentContact.DoesNotExist:
            return Response({'message': 'No parent contact found'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        serializer = ParentContactSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            parent_contact = serializer.save()
            
            # Update user's profile completion status
            request.user.check_profile_completion()
            
            return Response({
                'message': 'Parent contact submitted successfully. Verification code sent.',
                'parent_contact': ParentContactSerializer(parent_contact).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParentVerificationView(APIView):
    """Verify parent contact with code"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ParentVerificationSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            # Update user's profile completion status
            request.user.check_profile_completion()
            
            return Response({
                'message': 'Parent contact verified successfully'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileCompletionView(APIView):
    """Check profile completion status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check completion status for each section
        try:
            identity_completed = user.identityinformation.is_verified
        except IdentityInformation.DoesNotExist:
            identity_completed = False
        
        try:
            education_completed = bool(user.educationalprofile)
        except EducationalProfile.DoesNotExist:
            education_completed = False
        
        try:
            location_completed = bool(user.location)
        except Location.DoesNotExist:
            location_completed = False
        
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
    """Get current user profile"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProtectedResourceView(APIView):
    """Example protected resource that requires complete profile"""
    permission_classes = [IsProfileCompletePermission]
    
    def get(self, request):
        return Response({
            'message': 'Access granted to protected resource',
            'user': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Location'],
    summary='List States',
    description='Get all available states/provinces'
)
class StateListView(generics.ListAPIView):
    """List all states"""
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


@extend_schema(
    tags=['Location'],
    summary='List Cities',
    description='Get cities, optionally filtered by state',
    parameters=[
        OpenApiParameter(
            name='state',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by state ID'
        )
    ]
)
class CityListView(generics.ListAPIView):
    """List cities for a specific state"""
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        state_id = self.request.query_params.get('state', None)
        if state_id:
            return City.objects.filter(state_id=state_id)
        return City.objects.all()
