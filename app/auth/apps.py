from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.auth"
    label = "custom_auth"

    def ready(self):
        import app.auth.schema  # noqa: F401
