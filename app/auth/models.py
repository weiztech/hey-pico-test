from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.functional import cached_property
from ulid import ULID

from .constants import AccessPermission as AccessPermissionChoices
from .managers import UserManager


def generate_ulid() -> str:
    return str(ULID())


class User(AbstractUser):
    id = models.CharField(
        max_length=26,
        primary_key=True,
        default=generate_ulid,
        editable=False,
    )
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self) -> str:
        return self.email


def generate_access_token():
    from uuid import uuid4

    return uuid4().hex


class AccessToken(models.Model):
    id = models.CharField(
        max_length=26,
        primary_key=True,
        default=generate_ulid,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_tokens",
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        default=generate_access_token,
    )
    rate_limit = models.PositiveIntegerField(
        default=60,
        help_text="Allowed requests per second for this token.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def get_active_permissions(self):
        """Return a queryset of active AccessPermission objects for this token."""
        return self.permissions.filter(is_active=True).distinct()

    @cached_property
    def rate_limit_prefix(self) -> str:
        """Generate the Redis key for rate limiting this token."""
        return f"rt:{self.pk}"

    def allow_request(self) -> bool:
        from app.common.utils.rate_limit import RateLimit

        return RateLimit.has_rate_limit(self.rate_limit_prefix, int(self.rate_limit))

    def __str__(self) -> str:
        return f"AccessToken(user={self.user_id}, token={self.token[:8]}...)"


class AccessPermission(models.Model):
    token = models.ForeignKey(
        AccessToken,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_permissions",
    )
    permission = models.CharField(
        max_length=100,
        choices=AccessPermissionChoices.choices,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token", "user", "permission", "is_active"]),
            models.Index(fields=["user", "permission"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["token", "permission"],
                name="unique_token_permission",
            )
        ]

    def __str__(self) -> str:
        return (
            f"Tool: AccessPermission(user={self.user_id}, permission={self.permission})"
        )
