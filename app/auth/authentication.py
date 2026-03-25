from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.permissions import BasePermission

from .models import AccessPermission, AccessToken


class AccessTokenAuthentication(BaseAuthentication):
    """
    DRF authentication backend that validates requests using the AccessToken model.

    Clients must pass the token in the Authorization header:

        Authorization: Bearer <token>

    Returns (token.user, token) on success so that request.user and
    request.auth are both available downstream.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "").strip()

        if not auth_header:
            # No credentials supplied — let other authenticators try.
            return None

        parts = auth_header.split()

        if len(parts) == 1:
            raise AuthenticationFailed(
                "Invalid Authorization header: no token provided."
            )

        if len(parts) > 2:
            raise AuthenticationFailed(
                "Invalid Authorization header: token string should not contain spaces."
            )

        keyword, raw_token = parts

        if keyword.lower() != self.keyword.lower():
            # Wrong scheme (e.g. Basic, Token) — not our concern.
            return None

        return self._authenticate_token(raw_token)

    def _authenticate_token(self, raw_token: str):
        try:
            access_token = AccessToken.objects.select_related("user").get(  # type: ignore[attr-defined]
                token=raw_token, is_active=True
            )
        except AccessToken.DoesNotExist:  # type: ignore[attr-defined]
            raise AuthenticationFailed("Invalid or inactive token.")

        if access_token.expires_at and access_token.expires_at < timezone.now():
            raise AuthenticationFailed("Token has expired.")

        if not access_token.user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        if not access_token.allow_request():
            raise Throttled(detail="Request rate limit exceeded for this token.")

        return (access_token.user, access_token)

    def authenticate_header(self, request) -> str | None:  # type: ignore[override]
        """
        Returned as the WWW-Authenticate header value on 401 responses,
        prompting clients to supply a Bearer token.
        """
        return self.keyword


class HasAccessPermission(BasePermission):
    """
    DRF permission class that checks whether an active AccessPermission record
    exists for the authenticated token and the permission required by the view.

    Views (or their ViewSet base class) declare the required permission via:

        required_permission: AccessPermission | None = AccessPermission.GOOGLE_MAP_API

    If ``required_permission`` is None the check is skipped and access is
    granted (authentication alone is sufficient).  When it is set, an active
    AccessPermission row must exist for both the token and the user.
    """

    message = "This token does not have permission to access this integration."

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        required_permission = getattr(view, "required_permission", None)

        # No specific permission declared — authenticated access is enough.
        if required_permission is None:
            return True

        # request.auth is the AccessToken instance set by AccessTokenAuthentication.
        access_token = request.auth
        if access_token is None:
            return False

        return AccessPermission.objects.filter(  # type: ignore[attr-defined]
            token=access_token,
            user=access_token.user,
            permission=required_permission.value,
            is_active=True,
        ).exists()
