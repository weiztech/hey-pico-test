import time
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from app.api_tools.integrations.other_3rd_party_api.views import (
    OtherThirdPartyApiViewSet,
)
from app.api_tools.urls import _basename
from app.auth.constants import AccessPermission as AccessPermissionChoices
from app.auth.models import AccessPermission, AccessToken, User


class TestAccessToken(TestCase):
    """
    Permission and rate-limit tests for the lucky_star_number endpoint.

    Two test methods:
      - test_permission  : verifies granted / denied scenarios via HTTP status codes.
      - test_rate_limit  : verifies HTTP 429 enforcement and allow_request() logic.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        basename = _basename(AccessPermissionChoices.OTHER_3RD_PARTY_API)
        url_name = OtherThirdPartyApiViewSet.lucky_star_number.url_name  # type: ignore[attr-defined]
        cls.LUCKY_STAR_URL = reverse(f"api_tools:{basename}-{url_name}")

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpass123",
        )

        # Primary token — generous limit so the rate limiter never fires
        # unless explicitly mocked.
        self.token = AccessToken.objects.create(
            user=self.user,
            rate_limit=100,
        )

        # Grant OTHER_3RD_PARTY_API to the primary token.
        self.access_permission = AccessPermission.objects.create(
            token=self.token,
            user=self.user,
            permission=AccessPermissionChoices.OTHER_3RD_PARTY_API,
            is_active=True,
        )

    def _auth(self, token: AccessToken | None = None) -> dict:
        """Return APIClient kwargs that set the Bearer Authorization header."""
        tok = token or self.token
        return {"HTTP_AUTHORIZATION": f"Bearer {tok.token}"}

    def _make_redis_mock(self, incr_result: int) -> MagicMock:
        """
        Return a mock Redis client whose pipeline().execute() returns
        [incr_result, True], matching the real (INCR, EXPIRE) pipeline.
        """
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [incr_result, True]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        return mock_redis

    def test_permission(self):
        """
        Verify that HasAccessPermission grants or denies access to
        lucky_star_number based on the token's AccessPermission rows.

        allow_request is patched to True throughout so that the rate limiter
        never interferes with the permission outcome.
        """
        with patch.object(AccessToken, "allow_request", return_value=True):
            # --- granted: active permission row present ---
            with self.subTest("granted — active OTHER_3RD_PARTY_API permission"):
                response = self.client.get(self.LUCKY_STAR_URL, **self._auth())
                self.assertEqual(response.status_code, 200)
                self.assertIn("content", response.data)
                self.assertGreaterEqual(response.data["content"], 1)
                self.assertLessEqual(response.data["content"], 1000)

            # --- denied: no permission row ---
            with self.subTest("denied — token has no permission row"):
                token_no_perm = AccessToken.objects.create(
                    user=self.user, rate_limit=100
                )
                response = self.client.get(
                    self.LUCKY_STAR_URL, **self._auth(token_no_perm)
                )
                self.assertEqual(response.status_code, 403)

            # --- denied: permission row is inactive ---
            with self.subTest("denied — permission row is inactive"):
                self.access_permission.is_active = False
                self.access_permission.save()
                response = self.client.get(self.LUCKY_STAR_URL, **self._auth())
                self.assertEqual(response.status_code, 403)
                # restore for any subsequent subtests
                self.access_permission.is_active = True
                self.access_permission.save()

            # --- denied: no Authorization header at all ---
            with self.subTest("denied — missing Authorization header"):
                response = self.client.get(self.LUCKY_STAR_URL)
                self.assertEqual(response.status_code, 401)

            # --- denied: token string does not exist ---
            with self.subTest("denied — invalid token string"):
                response = self.client.get(
                    self.LUCKY_STAR_URL,
                    HTTP_AUTHORIZATION="Bearer token-that-does-not-exist",
                )
                self.assertEqual(response.status_code, 401)

            # --- denied: token is deactivated ---
            with self.subTest("denied — token is_active=False"):
                self.token.is_active = False
                self.token.save()
                response = self.client.get(self.LUCKY_STAR_URL, **self._auth())
                self.assertEqual(response.status_code, 401)
                self.token.is_active = True
                self.token.save()

    def test_rate_limit(self):
        """
        Verify that the rate limiter returns HTTP 429 when the per-second
        budget is exhausted, and that allow_request() enforces the correct
        Redis fixed-window logic.
        """

        # --- HTTP level: within budget → 200 ---
        with self.subTest("HTTP 200 — allow_request returns True"):
            with patch.object(AccessToken, "allow_request", return_value=True):
                response = self.client.get(self.LUCKY_STAR_URL, **self._auth())
            self.assertEqual(response.status_code, 200)
            self.assertIn("content", response.data)

        # --- HTTP level: budget exhausted → 429 ---
        with self.subTest("HTTP 429 — allow_request returns False"):
            with patch.object(AccessToken, "allow_request", return_value=False):
                response = self.client.get(self.LUCKY_STAR_URL, **self._auth())
            self.assertEqual(response.status_code, 429)

        # --- model: counter below limit → True ---
        with self.subTest("allow_request True — counter below rate_limit"):
            self.token.rate_limit = 10
            with patch(
                "app.common.utils.redis_client.get_redis_client",
                return_value=self._make_redis_mock(5),
            ):
                self.assertTrue(self.token.allow_request())

        # --- model: counter exactly at limit → True (inclusive boundary) ---
        with self.subTest("allow_request True — counter equals rate_limit"):
            self.token.rate_limit = 10
            with patch(
                "app.common.utils.redis_client.get_redis_client",
                return_value=self._make_redis_mock(10),
            ):
                self.assertTrue(self.token.allow_request())

        # --- model: counter one over limit → False ---
        with self.subTest("allow_request False — counter exceeds rate_limit"):
            self.token.rate_limit = 10
            with patch(
                "app.common.utils.redis_client.get_redis_client",
                return_value=self._make_redis_mock(11),
            ):
                self.assertFalse(self.token.allow_request())

        # --- model: first request in a fresh window is always allowed ---
        with self.subTest(
            "allow_request True — first request (counter == 1, rate_limit == 1)"
        ):
            self.token.rate_limit = 1
            with patch(
                "app.common.utils.redis_client.get_redis_client",
                return_value=self._make_redis_mock(1),
            ):
                self.assertTrue(self.token.allow_request())

        # --- model: Redis key is scoped to token PK and current second ---
        with self.subTest(
            "allow_request — Redis key contains token PK and Unix second"
        ):
            self.token.rate_limit = 100
            frozen_second = 1_700_000_000
            mock_redis = self._make_redis_mock(1)
            with (
                patch(
                    "app.common.utils.redis_client.get_redis_client",
                    return_value=mock_redis,
                ),
                patch("app.common.utils.rate_limit.time") as mock_time,
            ):
                mock_time.return_value = frozen_second
                self.token.allow_request()
            expected_key = f"{self.token.rate_limit_prefix}:{frozen_second}"
            mock_redis.pipeline.return_value.incr.assert_called_once_with(expected_key)

        # --- model: EXPIRE TTL is 2 seconds ---
        with self.subTest("allow_request — EXPIRE TTL is 2 seconds"):
            self.token.rate_limit = 100
            mock_redis = self._make_redis_mock(1)
            with patch(
                "app.common.utils.redis_client.get_redis_client",
                return_value=mock_redis,
            ):
                self.token.allow_request()
            _key, ttl = mock_redis.pipeline.return_value.expire.call_args.args
            self.assertEqual(ttl, 2)

        # --- model: pipeline is always executed ---
        with self.subTest("allow_request — pipeline.execute() is called once"):
            self.token.rate_limit = 100
            mock_redis = self._make_redis_mock(1)
            with patch(
                "app.common.utils.redis_client.get_redis_client",
                return_value=mock_redis,
            ):
                self.token.allow_request()
            mock_redis.pipeline.return_value.execute.assert_called_once()

        # --- real Redis: burst to limit, blocked, resets on next second ---
        with self.subTest("real Redis — burst hits limit then resets next second"):
            from app.common.utils.redis_client import get_redis_client

            # Skip gracefully if Redis is not reachable.
            try:
                r = get_redis_client()
                r.ping()
            except Exception:
                self.skipTest("Redis not available — skipping real-Redis subtest")

            RATE_LIMIT = 5
            self.token.rate_limit = RATE_LIMIT

            # Flush any leftover keys from previous runs.
            for key in r.scan_iter(f"{self.token.rate_limit_prefix}:*"):
                r.delete(key)

            # Align to a fresh second so the burst cannot straddle a boundary.
            # remaining = 1.0 - (time.time() % 1.0)
            # if remaining < 0.3:  # too close to the edge — wait for next one
            #    time.sleep(remaining + 0.05)

            # RATE_LIMIT requests must all succeed within the same second.
            for i in range(RATE_LIMIT):
                self.assertTrue(
                    self.token.allow_request(),
                    f"Request {i + 1}/{RATE_LIMIT} should be allowed",
                )

            # One more request in the same window must be blocked.
            self.assertFalse(
                self.token.allow_request(),
                f"Request {RATE_LIMIT + 1} should be blocked (limit exhausted)",
            )

            # Sleep until the next second window opens.
            time.sleep(1.0 - (time.time() % 1.0) + 0.001)

            # First request in the new window must succeed again.
            self.assertTrue(
                self.token.allow_request(),
                "First request after window reset should be allowed",
            )

            # Cleanup.
            for key in r.scan_iter(f"{self.token.rate_limit_prefix}:*"):
                r.delete(key)
