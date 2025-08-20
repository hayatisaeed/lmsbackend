from django.urls import path

from .views import (
    LogoutView,
    RefreshView,
    RequestOTPView,
    SessionView,
    VerifyOTPView,
)

urlpatterns = [
    path("auth/request-otp", RequestOTPView.as_view()),
    path("auth/verify-otp", VerifyOTPView.as_view()),
    path("auth/refresh", RefreshView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("auth/session", SessionView.as_view()),
]
