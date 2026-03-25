from app.auth.constants import AccessPermission

from .integrations.google_map.views import GoogleMapViewSet
from .integrations.my_other_api.views import MyOtherApiViewSet
from .integrations.other_3rd_party_api.views import OtherThirdPartyApiViewSet

# Single place to change if the tools mount point ever moves.
API_TOOLS_MOUNT = "api/tools/"

# Maps each AccessPermission to its URL slug and ViewSet.
# url_prefix is derived as f"/{API_TOOLS_MOUNT}{slug}/" wherever needed.
INTEGRATIONS: dict[AccessPermission, dict] = {
    AccessPermission.GOOGLE_MAP_API: {
        "slug": "google-map",
        "viewset": GoogleMapViewSet,
    },
    AccessPermission.MY_API: {
        "slug": "my-other-api",
        "viewset": MyOtherApiViewSet,
    },
    AccessPermission.OTHER_3RD_PARTY_API: {
        "slug": "other-3rd-party-api",
        "viewset": OtherThirdPartyApiViewSet,
    },
}
