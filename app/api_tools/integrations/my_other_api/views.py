from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from app.api_tools.base import IntegrationViewSet
from app.auth.constants import AccessPermission

from .serializers import CustomSumInputSerializer, CustomSumOutputSerializer


@extend_schema(tags=["My API"])
class MyOtherApiViewSet(IntegrationViewSet):
    required_permission = AccessPermission.MY_API
    API_TITLE = "PICO Test: My API"
    API_VERSION = "0.1.0"
    API_DESCRIPTION = "My Other API integration endpoints."

    @extend_schema(
        summary="Custom Sum",
        description="Accepts two operands",
        operation_id="custom-sum",
        request=CustomSumInputSerializer,
        responses={
            200: OpenApiResponse(
                response=CustomSumOutputSerializer,
                description="Sum computed successfully.",
                examples=[
                    OpenApiExample(
                        name="Integer inputs",
                        request_only=False,
                        value={"result": "7"},
                    ),
                    OpenApiExample(
                        name="Numeric string inputs",
                        request_only=False,
                        value={"result": "3.14"},
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid input — non-numeric value supplied."
            ),
        },
    )
    @action(detail=False, methods=["post"], url_path="custom-sum")
    def custom_sum(self, request, *args, **kwargs):
        input_serializer = CustomSumInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        a = input_serializer.validated_data["a"]  # type: ignore[index]
        b = input_serializer.validated_data["b"]  # type: ignore[index]

        # if one of a or b is not number then just convert both to string and concatenate them
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            a = str(a)
            b = str(b)

        result = a + b  # type: ignore[operator]

        output_serializer = CustomSumOutputSerializer({"result": result})
        return Response(output_serializer.data)
