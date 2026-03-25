from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AccessPermission, AccessToken, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "last_login",
        "date_joined",
    )
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )


class AccessPermissionInline(admin.TabularInline):
    model = AccessPermission
    extra = 0
    fields = ("permission", "is_active", "created_at")
    readonly_fields = ("created_at",)
    verbose_name = "Tool Access Permission"
    verbose_name_plural = "Tool Access Permissions"


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    inlines = [AccessPermissionInline]
    list_display = (
        "id",
        "user",
        "token_short",
        "rate_limit",
        "is_active",
        "created_at",
        "expires_at",
    )
    list_filter = ("is_active", "created_at", "expires_at")
    search_fields = ("token", "user__email", "user__first_name", "user__last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)

    fieldsets = (
        (
            "Token Details",
            {
                "fields": (
                    "user",
                    "token",
                    "is_active",
                    "rate_limit",
                    "expires_at",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at",),
            },
        ),
    )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, AccessPermission):
                instance.user = form.instance.user
            instance.save()
        formset.save_m2m()

    @admin.display(description="Token")
    def token_short(self, obj: AccessToken) -> str:
        return f"{obj.token[:8]}..." if obj.token else "-"  # type: ignore[index]
