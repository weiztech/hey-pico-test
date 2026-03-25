from django.conf import settings
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import BasePermission


class HasValidToken(BasePermission):
    """
    Allow access only if a valid signed URL token is provided.
    """

    PREFIX_KEY = "TOKEN_AUTH_RATE_LIMIT_KEY"

    def has_permission(self, request, view):
        from app.common.utils.rate_limit import RateLimit
        from app.common.utils.signed_url import SignedURL

        token = request.query_params.get("token")

        if not token:
            raise ValidationError("token query parameter is required.")

        token_value = SignedURL.verify_token(
            token,
            secret_key=settings.SECRET_KEY,
            max_age=settings.SIGNED_URL_MAX_AGE,
        )

        # Check rate limit for this token if a prefix key is defined on the view
        token_auth_rate_limit_key = getattr(view, self.PREFIX_KEY, None)
        if token_auth_rate_limit_key:
            rate_limit_key = f"{token_auth_rate_limit_key}:{token_value}"
            if not RateLimit.has_rate_limit(
                rate_limit_key,
                rate_limit=settings.SIGNED_URL_RATE_LIMIT,
            ):
                raise Throttled(detail="Rate limit per second exceeded for this token.")

        request.signed_token_value = token_value  # type: ignore[attr-defined]
        return bool(token_value)
