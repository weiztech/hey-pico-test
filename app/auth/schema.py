from drf_spectacular.extensions import OpenApiAuthenticationExtension


class AccessTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "app.auth.authentication.AccessTokenAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "hex token",
            "description": (
                "Token-based authentication. "
                "Pass the token in the Authorization header as: Bearer <token>"
            ),
        }
