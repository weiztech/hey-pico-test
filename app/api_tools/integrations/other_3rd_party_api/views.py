import random

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from app.api_tools.base import IntegrationViewSet
from app.auth.constants import AccessPermission

from .serializers import LuckyStarNumberOutputSerializer


@extend_schema(tags=["Other 3rd Party API"])
class OtherThirdPartyApiViewSet(IntegrationViewSet):
    required_permission = AccessPermission.OTHER_3RD_PARTY_API
    API_TITLE = "PICO Test: Other 3rd Party API"
    API_VERSION = "0.0.1"
    API_DESCRIPTION = "Integration endpoints for Other 3rd Party API."

    @extend_schema(
        summary="Lucky Star Number",
        description=(
            "Returns a randomly generated lucky star number between 1 and 1000 "
            "(inclusive). Each request produces an independent random draw."
        ),
        responses={
            200: OpenApiResponse(
                response=LuckyStarNumberOutputSerializer,
                description="A lucky star number was successfully generated.",
                examples=[
                    OpenApiExample(
                        name="Example response",
                        value={"content": 42},
                    ),
                ],
            ),
        },
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="lucky-star-number",
        url_name="lucky-star",
    )
    def lucky_star_number(self, request, *args, **kwargs):
        serializer = LuckyStarNumberOutputSerializer(
            {"content": random.randint(1, 1000)}
        )
        return Response(serializer.data)
