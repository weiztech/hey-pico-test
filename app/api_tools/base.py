from typing import Any

from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from app.auth.authentication import HasAccessPermission
from app.auth.constants import AccessPermission


class IntegrationViewSet(ViewSet):
    permission_classes = [HasAccessPermission]

    required_permission: AccessPermission | None = None

    API_TITLE: str = "Integration API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Base integration API."

    @staticmethod
    def _collect_schema_refs(obj: Any) -> set[str]:
        """Recursively collect all $ref values from a schema fragment."""
        refs: set[str] = set()
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    refs.add(value)
                else:
                    refs.update(IntegrationViewSet._collect_schema_refs(value))
        elif isinstance(obj, list):
            for item in obj:
                refs.update(IntegrationViewSet._collect_schema_refs(item))
        return refs

    @staticmethod
    def _build_integration_schema(
        full_schema: dict,
        url_prefix: str,
        viewset: "type[IntegrationViewSet]",
    ) -> dict:
        """
        Slice a full project OpenAPI schema down to a single integration.

        Filters paths to those starting with ``url_prefix`` (excluding the
        ``/connect/`` meta-endpoint itself) and overwrites the info block with
        the viewset's own title/version/description.  Component schemas are
        pruned to only those actually referenced by the remaining paths so that
        sibling integrations' definitions don't leak in.

        Used by both :meth:`connect` (where the prefix is derived from the
        request path) and the list-tools view (where it is looked up from the
        integration registry).
        """
        schema: dict = {
            **full_schema,
            "info": {
                "title": viewset.API_TITLE,
                "version": viewset.API_VERSION,
                "description": viewset.API_DESCRIPTION,
            },
            "paths": {
                path: operations
                for path, operations in full_schema.get("paths", {}).items()
                if path.startswith(url_prefix) and not path.endswith("connect/")
            },
        }

        # Prune components/schemas to only those referenced by the filtered
        # paths so that sibling integrations' schemas don't leak in.
        components = dict(full_schema.get("components", {}))
        all_schemas = components.get("schemas", {})
        if all_schemas:
            used = {
                ref.split("/")[-1]
                for ref in IntegrationViewSet._collect_schema_refs(schema["paths"])
                if ref.startswith("#/components/schemas/")
            }
            schema["components"] = {
                **components,
                "schemas": {name: s for name, s in all_schemas.items() if name in used},
            }

        return schema

    @extend_schema(
        summary="OpenAPI schema for this integration",
        description=(
            "Returns the OpenAPI schema scoped to this integration only. "
            "The schema info block reflects the title, version, and description "
            "defined on the integration's ViewSet class."
        ),
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="OpenAPI schema object for the integration.",
            ),
        },
    )
    @action(detail=False, methods=["get"], url_path="connect")
    def connect(self, request, *args, **kwargs):
        """
        Returns the OpenAPI schema scoped to this integration only.

        Derives the integration prefix from the current request path
        (e.g. /api/tools/google-map/connect/ -> /api/tools/google-map/)
        and delegates to :meth:`_build_integration_schema`.
        """
        prefix = request.path.rsplit("connect/", 1)[0]

        generator = SchemaGenerator()
        full_schema = generator.get_schema(request=request, public=True) or {}

        return Response(self._build_integration_schema(full_schema, prefix, type(self)))
