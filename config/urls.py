from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/healthz", views.healthz, name="healthz"),
    path("api/v1/readyz", views.readyz, name="readyz"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",
    ),
    path("api/v1/metrics", views.metrics, name="metrics"),
    path("api/v1/", include("apps.users.urls")),
]
