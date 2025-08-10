from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.UnifiedLoginView.as_view(), name='unified_login'),
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/verify/otp/', views.OTPVerificationView.as_view(), name='otp_verify'),
    path('auth/login/password/', views.PasswordLoginView.as_view(), name='password_login'),
    path('auth/test-info/', views.TestPhoneInfoView.as_view(), name='test_phone_info'),
    
    # Educational data endpoints
    path('educational-levels/', views.EducationalLevelListView.as_view(), name='educational_levels'),
    path('study-branches/', views.StudyBranchListView.as_view(), name='study_branches'),
    path('olympiads/', views.OlympiadListView.as_view(), name='olympiads'),
    
    # Location data endpoints
    path('states/', views.StateListView.as_view(), name='states'),
    path('cities/', views.CityListView.as_view(), name='cities'),
    
    # Profile completion endpoints
    path('profile/identity/', views.IdentityInformationView.as_view(), name='identity'),
    path('profile/education/', views.EducationalProfileView.as_view(), name='education'),
    path('profile/parent/', views.ParentContactView.as_view(), name='parent_contact'),
    path('profile/parent/verify/', views.ParentVerificationView.as_view(), name='parent_verify'),
    path('profile/completion/', views.ProfileCompletionView.as_view(), name='profile_completion'),
    
    # User profile
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    
    # Protected resource example
    path('protected/', views.ProtectedResourceView.as_view(), name='protected_resource'),
] 