"""
URL configuration for config project.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from app.api_tools.registry import API_TOOLS_MOUNT

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/health/",
        lambda request: JsonResponse({"status": "ok", "service": "test-heypico"}),
        name="health-check",
    ),
    path(API_TOOLS_MOUNT, include("app.api_tools.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
