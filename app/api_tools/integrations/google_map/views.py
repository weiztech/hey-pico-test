from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from app.api_tools.base import IntegrationViewSet
from app.api_tools.permissions import HasValidToken
from app.auth.constants import AccessPermission

from .serializers import GetLocationInfoInputSerializer, GetLocationInfoOutputSerializer
from .services import GoogleMapServices

MAP_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Map - {query}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ overflow: hidden; }}
        iframe {{ border: 0; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; }}
    </style>
</head>
<body>
    <iframe
        loading="lazy"
        allowfullscreen
        referrerpolicy="no-referrer-when-downgrade"
        src="https://www.google.com/maps/embed/v1/place?key={api_key}&q={encoded_query}">
    </iframe>
</body>
</html>"""


@extend_schema(tags=["Google Map"])
class GoogleMapViewSet(IntegrationViewSet):
    required_permission = AccessPermission.GOOGLE_MAP_API
    API_TITLE = "PICO Test: Google Map API"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "Integration endpoints for Google Map API."
    TOKEN_AUTH_RATE_LIMIT_KEY = "gmap_rate_limit"

    @extend_schema(
        summary="Hello from Google Map",
        description=("Hello from API"),
        operation_id="say-hello",
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="GoogleMapHelloResponse",
                    fields={
                        # "integration": serializers.CharField(),
                        # "message": serializers.CharField(),
                        "content": serializers.CharField(),
                    },
                ),
                description="Successful greeting response.",
                examples=[
                    OpenApiExample(
                        name="Success",
                        value={
                            # "integration": "string",
                            # "message": "string",
                            "content": "mark down string",
                        },
                    )
                ],
            ),
        },
    )
    @action(detail=False, methods=["get"], url_path="hello")
    def hello(self, request, *args, **kwargs):
        output = GoogleMapServices.get_location(
            location="Jakarta",
            keyword="Fried Chicken",
            type="cafe",
        )
        simplified = GoogleMapServices.simple_output(output)
        return Response(
            {
                # "integration": "google_map",
                # "message": "Hello My Name is Magby",
                # "content": "Hello, Here’s a sample image:\n![GitHub Logo](https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png)\n\nHere is an interactive map: [Open in Google Maps](https://www.google.com/maps?q=Jakarta)",
                "content": f"Hello,\n\n  {simplified['content']}",
            }
        )

    @extend_schema(
        summary="Get Location Info",
        description="Search for nearby places based on a location, keyword, and type.",
        operation_id="get-location-info",
        request=GetLocationInfoInputSerializer,
        responses={
            200: OpenApiResponse(
                response=GetLocationInfoOutputSerializer,
                description="Nearby places found successfully.",
            ),
            400: OpenApiResponse(
                description="Invalid input.",
            ),
        },
    )
    @action(detail=False, methods=["post"], url_path="get-location-info")
    def get_location_info(self, request, *args, **kwargs):
        input_serializer = GetLocationInfoInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        validated = input_serializer.validated_data  # type: ignore[union-attr]
        location = validated["location"]  # type: ignore[index]
        keyword = validated["keyword"]  # type: ignore[index]
        place_type = validated["type"]  # type: ignore[index]
        next_page_token = validated.get("next_page_token")  # type: ignore[union-attr]

        raw_result = GoogleMapServices.get_location(
            location=location,
            keyword=keyword,
            type=place_type,
            next_page_token=next_page_token,
        )

        simplified = GoogleMapServices.simple_output(raw_result)

        output_serializer = GetLocationInfoOutputSerializer(simplified)
        return Response(output_serializer.data)

    @extend_schema(exclude=True)
    @action(
        detail=False,
        methods=["get"],
        url_path="map",
        permission_classes=[HasValidToken],
        authentication_classes=[],
    )
    def map(self, request, *args, **kwargs):
        """
        Renders an HTML page with an embedded Google Map based on a signed query token.
        This endpoint will not be documented in the OpenAPI schema
        """
        query_value = request.signed_token_value["q"].strip()
        html = MAP_HTML_TEMPLATE.format(
            query=query_value,
            encoded_query=quote(query_value, safe=""),
            api_key=settings.GOOGLE_MAPS_API_KEY,
        )
        return HttpResponse(html, content_type="text/html; charset=utf-8")  # type: ignore[arg-type]
