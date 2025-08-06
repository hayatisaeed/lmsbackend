from rest_framework import permissions
from .models import IdentityInformation, EducationalProfile, Location, ParentContact


class IsProfileCompletePermission(permissions.BasePermission):
    """
    Permission to check if user has completed their profile.
    Users must complete all required sections to access main features.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if user has completed all required profile sections
        try:
            identity = request.user.identityinformation
            education = request.user.educationalprofile
            location = request.user.location
            parent_contact = request.user.parentcontact
            
            # All sections must be completed and verified
            if (identity.is_verified and education and location and parent_contact.is_verified):
                return True
            else:
                return False
        except:
            return False


class IsIdentityVerifiedPermission(permissions.BasePermission):
    """
    Permission to check if user's identity is verified.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            identity = request.user.identityinformation
            return identity.is_verified
        except IdentityInformation.DoesNotExist:
            return False


class IsNotVerifiedPermission(permissions.BasePermission):
    """
    Permission for users who are not yet verified.
    Used for initial registration and profile completion.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Allow access if user is not profile complete
        return not request.user.is_profile_complete


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access for unauthenticated users.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated 