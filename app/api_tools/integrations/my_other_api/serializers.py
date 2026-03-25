from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


@extend_schema_field({"oneOf": [{"type": "number"}, {"type": "string"}]})
class NumberOrStringField(serializers.Field):
    """
    Accepts an integer, float, or a numeric string.

    Both ``3`` and ``"3"`` are valid values for the same field.
    Non-numeric strings are rejected with a validation error.
    """

    default_error_messages = {
        "invalid": '"{input}" is not a valid number or numeric string.',
    }

    def to_internal_value(self, data) -> int | float:
        if isinstance(data, bool):
            # bool is a subclass of int in Python — reject it explicitly.
            self.fail("invalid", input=data)

        if isinstance(data, (int, float)):
            return data

        if isinstance(data, str):
            try:
                return float(data) if "." in data else int(data)
            except ValueError:
                self.fail("invalid", input=data)

        self.fail("invalid", input=data)

    def to_representation(self, value) -> int | float:
        return value


class CustomSumInputSerializer(serializers.Serializer):
    a = NumberOrStringField(
        help_text="First operand — integer, float, or numeric string."
    )
    b = NumberOrStringField(
        help_text="Second operand — integer, float, or numeric string."
    )


class CustomSumOutputSerializer(serializers.Serializer):
    result = serializers.CharField(
        help_text="String representation of the sum of a and b."
    )
