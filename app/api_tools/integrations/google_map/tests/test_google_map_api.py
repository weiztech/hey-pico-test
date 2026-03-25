from signal import SIGABRT
from time import sleep

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from app.api_tools.integrations.google_map.services import GoogleMapServices
from app.api_tools.urls import _basename
from app.auth.constants import AccessPermission as AccessPermissionChoices
from app.common.utils.signed_url import SignedURL

FAKE_API_KEY = "test-fake-google-maps-api-key"


class TestGoogleMapAPI(TestCase):
    """
    Tests for the ``map`` endpoint on GoogleMapViewSet.

    The endpoint is unauthenticated (authentication_classes=[]) but protected
    by HasValidToken, which verifies a signed token passed as a query parameter.
    It renders an HTML page embedding a Google Map iframe for the query encoded
    in the token.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        basename = _basename(AccessPermissionChoices.GOOGLE_MAP_API)
        cls.MAP_URL = reverse(f"api_tools:{basename}-map")

    def setUp(self):
        self.client = APIClient()

    @override_settings(
        GOOGLE_MAPS_API_KEY=FAKE_API_KEY,
        SIGNED_URL_MAX_AGE=1,  # change to 1 second for testing expired token case easily
        SIGNED_URL_RATE_LIMIT=2,
    )
    def test_map_api(self):
        # test valid
        token = GoogleMapServices._build_signed_map_url("testing").split("?token=", 1)[
            1
        ]
        response = self.client.get(self.MAP_URL, {"token": token})
        self.assertEqual(response.status_code, 200)

        # test invalid token
        token = "invalid"
        response = self.client.get(self.MAP_URL, {"token": token})
        self.assertEqual(response.status_code, 400)

        # test with expire token
        token = SignedURL.generate_token(settings.SECRET_KEY, q="123")
        sleep(1.1)  # sleep for a bit longer than MAP_URL_MAX_AGE to ensure expiration
        response = self.client.get(self.MAP_URL, {"token": token})
        self.assertEqual(response.status_code, 400)

        # test rate limit exceeded
        token = SignedURL.generate_token(settings.SECRET_KEY, q="rate-limit-test")
        for _ in range(2):
            response = self.client.get(self.MAP_URL, {"token": token})
            self.assertEqual(response.status_code, 200)

        response = self.client.get(self.MAP_URL, {"token": token})
        self.assertEqual(response.status_code, 429)
