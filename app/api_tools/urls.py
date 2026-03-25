from django.urls import path
from rest_framework.routers import SimpleRouter

from app.auth.constants import AccessPermission

from .registry import INTEGRATIONS
from .views import ListToolView, MyToolSchemaView, MyToolView

app_name = "api_tools"


def _basename(permission: AccessPermission) -> str:
    """Derive a URL-safe basename from an AccessPermission value.

    Example: AccessPermission.GOOGLE_MAP_API ("Google Map API") -> "google-map-api"
    """
    return permission.value.lower().replace(" ", "-")


router = SimpleRouter(trailing_slash=True)
for permission, entry in INTEGRATIONS.items():
    router.register(entry["slug"], entry["viewset"], basename=_basename(permission))

urlpatterns = [
    path("list/", ListToolView.as_view(), name="list-tool-names"),
    path("available", MyToolView.as_view(), name="list-tools"),
    path("available/schema", MyToolSchemaView.as_view(), name="my-tool-schema"),
    *router.urls,
]
