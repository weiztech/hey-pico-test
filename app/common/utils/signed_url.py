from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from rest_framework.exceptions import ValidationError


class SignedURL:
    @staticmethod
    def generate_token(secret_key: str, **kwargs) -> str:
        """Generate a signed URL embedding the query in a tamper-proof token."""
        return signing.dumps(kwargs, salt=secret_key, compress=True)

    @staticmethod
    def verify_token(token: str, secret_key: str, max_age: int) -> dict:
        """Verify a signed URL token and return the query string.

        Raises ``django.core.signing.BadSignature`` if the token is
        invalid or expired.
        """
        try:
            data = signing.loads(token, salt=secret_key, max_age=max_age)
        except SignatureExpired:
            raise ValidationError("Map link has expired.")
        except BadSignature:
            raise ValidationError("Invalid map link.")

        return data
