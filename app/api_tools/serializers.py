from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from app.auth.constants import AccessPermission

from .base import IntegrationViewSet
from .registry import API_TOOLS_MOUNT, INTEGRATIONS


class ListToolsSerializer(serializers.ListSerializer):
    """
    List serializer that generates the full project OpenAPI schema once
    before delegating per-item serialization to ToolSerializer.

    Storing full_schema in the shared context avoids regenerating it for
    every item in the list.
    """

    def to_representation(self, data):
        request = self.context["request"]
        generator = SchemaGenerator()
        self.context["full_schema"] = (
            generator.get_schema(request=request, public=True) or {}
        )
        return super().to_representation(data)


class ToolSerializer(serializers.Serializer):
    """
    Serializes a single accessible integration tool for the authenticated token.

    permission  – the AccessPermission choice value (e.g. "Google Map API").
    schema      – the scoped OpenAPI schema, identical to what that
                  integration's own /connect/ endpoint would return.
    """

    tool_name = serializers.CharField(source="permission")
    schema = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_schema(self, obj) -> dict:
        full_schema = self.context.get("full_schema", {})
        entry = INTEGRATIONS.get(AccessPermission(obj.permission))
        if not entry:
            return {}
        return IntegrationViewSet._build_integration_schema(
            full_schema,
            f"/{API_TOOLS_MOUNT}{entry['slug']}/",
            entry["viewset"],
        )

    class Meta:
        list_serializer_class = ListToolsSerializer
