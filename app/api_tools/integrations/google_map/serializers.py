from rest_framework import serializers


class GetLocationInfoInputSerializer(serializers.Serializer):
    location = serializers.CharField(
        required=True,
        help_text="Location name or address to search near (e.g. 'Jakarta').",
    )
    keyword = serializers.CharField(
        required=True,
        help_text="Keyword to filter places (e.g. 'Makanan Pedas', 'Sate', 'Rendang').",
    )
    type = serializers.CharField(
        required=True,
        help_text="Place type to search for (e.g. 'restaurant', 'cafe', 'store').",
    )
    next_page_token = serializers.CharField(
        required=False,
        default=None,
        allow_null=True,
        allow_blank=True,
        help_text="Token for fetching the next page of results (Optional).",
    )


class PlaceSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    rating = serializers.FloatField(allow_null=True)
    total_ratings = serializers.IntegerField(allow_null=True)
    open_now = serializers.BooleanField(allow_null=True)
    business_status = serializers.CharField(allow_null=True)
    image_link = serializers.URLField(allow_null=True, default=None)
    map_link = serializers.URLField(allow_null=True, default=None)


class GetLocationInfoOutputSerializer(serializers.Serializer):
    data = PlaceSerializer(many=True)  # type: ignore[assignment]
    content = serializers.CharField(
        allow_blank=True,
        default="",
        help_text="Markdown-formatted summary of the results, including embedded images. used for rendering in the frontend.",
    )
    next_page_token = serializers.CharField(allow_null=True, default=None)
