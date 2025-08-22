from django.urls import path

from .profile_views import (
    EducationView,
    IdentityView,
    LocationView,
    ParentVerifyView,
    ParentView,
    ProfileCompletionView,
    ProfileView,
    UserAvatarAPIView,
)
from .taxonomy_views import (
    EducationalLevelListView,
    LocationListView,
    OlympiadListView,
    StudyBranchListView,
    SchoolTypeListView,
)
from .views import (
    LogoutView,
    RefreshView,
    RequestOTPView,
    SessionView,
    VerifyOTPView,
)

urlpatterns = [
    # Authentication Views and Endpoints
    path("auth/request-otp", RequestOTPView.as_view()),
    path("auth/verify-otp", VerifyOTPView.as_view()),
    path("auth/refresh", RefreshView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("auth/session", SessionView.as_view()),

    # Profile Views and Endpoints
    path("profile/identity", IdentityView.as_view()),
    path("profile/education", EducationView.as_view()),
    path("profile/location", LocationView.as_view()),
    path("profile/parent", ParentView.as_view()),
    path("profile/parent/verify", ParentVerifyView.as_view()),
    path("profile", ProfileView.as_view()),
    path("profile/completion", ProfileCompletionView.as_view()),
    path("profile/avatar", UserAvatarAPIView.as_view()),

    # Taxonomy Views and Endpoints
    path("educational-levels", EducationalLevelListView.as_view()),
    path("study-branches", StudyBranchListView.as_view()),
    path("olympiads", OlympiadListView.as_view()),
    path("locations", LocationListView.as_view()),
    path("school-types", SchoolTypeListView.as_view()),
]
