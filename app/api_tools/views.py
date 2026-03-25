from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from app.auth.constants import AccessPermission

from .base import IntegrationViewSet
from .registry import API_TOOLS_MOUNT, INTEGRATIONS
from .serializers import ToolSerializer


class ToolsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ListToolView(APIView):
    """Returns the names of all tools defined in the AccessPermission enum."""

    @extend_schema(
        summary="List all tool names",
        description="Returns the name of every tool defined in the AccessPermission enum, regardless of what the current token is permitted to use.",
        responses={
            200: OpenApiResponse(
                response=serializers.ListSerializer(child=serializers.CharField()),
                description="A flat list of tool name strings.",
                examples=[
                    OpenApiExample(
                        name="Example",
                        value=["Google Map API", "My API", "Other 3rd party API"],
                    )
                ],
            )
        },
    )
    def get(self, request):
        return Response([p.value for p in AccessPermission])


class MyToolView(GenericAPIView):
    """
    Returns all integrations the current access token is permitted to use,
    each accompanied by its scoped OpenAPI schema (identical to the output
    of that integration's /connect/ endpoint).
    """

    serializer_class = ToolSerializer
    pagination_class = ToolsPagination

    def get_queryset(self):
        return self.request.auth.get_active_permissions()

    @extend_schema(
        summary="List accessible tools",
        description=(
            "Returns every integration for which the authenticated access token "
            "holds an active permission, together with its scoped OpenAPI schema. "
            "The schema for each tool is identical to what that integration's own "
            "`/connect/` endpoint would return."
        ),
        responses=ToolSerializer(many=True),
    )
    def get(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MyToolSchemaView(APIView):
    """
    Returns a single merged OpenAPI specification containing only the
    paths that the authenticated access token is permitted to use.
    """

    @extend_schema(
        summary="My tool schema",
        description=(
            "Returns a merged OpenAPI spec whose paths are scoped to the "
            "integrations the authenticated token has active permissions for."
        ),
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Merged OpenAPI schema filtered by token permissions.",
            ),
        },
    )
    def get(self, request):
        # Generate the full project OpenAPI schema once
        generator = SchemaGenerator()
        full_schema = generator.get_schema(request=request, public=True) or {}

        # Collect the permissions the token holds
        active_perms = request.auth.get_active_permissions()
        permitted_values = set(active_perms.values_list("permission", flat=True))

        # Merge paths & component schemas for every permitted integration
        merged_paths: dict = {}
        merged_schemas: dict = {}

        for perm_value in permitted_values:
            try:
                perm_enum = AccessPermission(perm_value)
            except ValueError:
                continue

            entry = INTEGRATIONS.get(perm_enum)
            if not entry:
                continue

            scoped = IntegrationViewSet._build_integration_schema(
                full_schema,
                f"/{API_TOOLS_MOUNT}{entry['slug']}/",
                entry["viewset"],
            )
            merged_paths.update(scoped.get("paths", {}))
            merged_schemas.update(scoped.get("components", {}).get("schemas", {}))

        # Build the final merged spec
        schema: dict = {
            "openapi": full_schema.get("openapi", "3.0.3"),
            "info": {
                "title": "My Tools",
                "version": "1.0.0",
                "description": "OpenAPI spec scoped to the current token's permitted tools.",
            },
            "paths": merged_paths,
        }

        if merged_schemas:
            schema["components"] = {"schemas": merged_schemas}

        return Response(schema)
