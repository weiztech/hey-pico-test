from rest_framework import serializers


class LuckyStarNumberOutputSerializer(serializers.Serializer):
    content = serializers.IntegerField(
        help_text="A random lucky star number between 1 and 1000."
    )
