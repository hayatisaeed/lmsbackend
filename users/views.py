from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction

from .models import (
    User, IdentityInformation, EducationalLevel, StudyBranch, Olympiad,
    EducationalProfile, Location, ParentContact
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, OTPRequestSerializer,
    OTPVerificationSerializer, PasswordLoginSerializer, EducationalLevelSerializer,
    StudyBranchSerializer, OlympiadSerializer, IdentityInformationSerializer,
    EducationalProfileSerializer, LocationSerializer, ParentContactSerializer,
    ParentVerificationSerializer, ProfileCompletionSerializer
)
from .permissions import (
    IsProfileCompletePermission, IsIdentityVerifiedPermission,
    IsNotVerifiedPermission, IsAuthenticatedOrReadOnly
)


class UserRegistrationView(APIView):
    """User registration with phone and display name"""
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


class OTPRequestView(APIView):
    """Request OTP for phone number"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPVerificationView(APIView):
    """Verify OTP and return JWT tokens"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            try:
                user = User.objects.get(phone=phone)
                refresh = RefreshToken.for_user(user)
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class EducationalLevelListView(generics.ListAPIView):
    """List all educational levels"""
    queryset = EducationalLevel.objects.all()
    serializer_class = EducationalLevelSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class StudyBranchListView(generics.ListAPIView):
    """List study branches for a specific level"""
    serializer_class = StudyBranchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        level_id = self.request.query_params.get('level', None)
        if level_id:
            return StudyBranch.objects.filter(level_id=level_id)
        return StudyBranch.objects.all()


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


class LocationView(APIView):
    """Handle location information submission"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            location = request.user.location
            serializer = LocationSerializer(location)
            return Response(serializer.data)
        except Location.DoesNotExist:
            return Response({'message': 'No location information found'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        serializer = LocationSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            location = serializer.save()
            
            # Update user's profile completion status
            request.user.check_profile_completion()
            
            return Response({
                'message': 'Location information submitted successfully',
                'location': LocationSerializer(location).data
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
