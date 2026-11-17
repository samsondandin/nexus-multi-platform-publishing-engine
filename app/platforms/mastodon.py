"""Mastodon (REST API) platform adapter."""

from datetime import datetime
import httpx
from app.config import settings
from app.platforms.base import BasePlatformAdapter
from app.schemas import PlatformResult
from app.utils.logging import logger


class MastodonAdapter(BasePlatformAdapter):
    """Adapter for Mastodon using the official REST API v1 (POST /api/v1/statuses).

    API Flow:
    1. Authenticate with instance using Bearer token with 'write:statuses' scope.
    2. Send POST /api/v1/statuses with `status` and `visibility: public`.
    3. Mastodon returns 200 OK with status object containing `url`, `created_at`, `visibility`.
    4. Compute public post URL directly from response `url`.
    5. Return normalized PlatformResult.
    """

    @property
    def platform_name(self) -> str:
        return "Mastodon"

    @property
    def public_access_supported(self) -> bool:
        return True

    @property
    def docs_url(self) -> str:
        return "https://docs.joinmastodon.org/methods/statuses/"

    @property
    def description(self) -> str:
        return "Federated open-source social network using the Mastodon REST API."

    def is_configured(self) -> bool:
        return bool(settings.MASTODON_INSTANCE_URL and settings.MASTODON_ACCESS_TOKEN)

    async def publish(self, message: str) -> PlatformResult:
        if not self.is_configured():
            return self.create_unconfigured_result()

        instance_url = settings.MASTODON_INSTANCE_URL.rstrip("/")
        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS)

        headers = {
            "Authorization": f"Bearer {settings.MASTODON_ACCESS_TOKEN}",
            "User-Agent": "nexus-publishing-engine/1.0",
        }
        payload = {
            "status": message,
            "visibility": "public",
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(
                    f"{instance_url}/api/v1/statuses",
                    headers=headers,
                    data=payload,
                )

                if resp.status_code == 401 or resp.status_code == 403:
                    return self.create_failed_result("Authentication failed: Invalid or unauthorized Mastodon access token.")
                elif resp.status_code == 422:
                    return self.create_failed_result(f"Unprocessable status payload: {resp.text}")
                elif resp.status_code == 429:
                    return self.create_failed_result("Mastodon rate limit exceeded (HTTP 429).")
                elif resp.is_error:
                    return self.create_failed_result(
                        f"Mastodon posting error (HTTP {resp.status_code}): {resp.text}"
                    )

                data = resp.json()
                posted_url = data.get("url")
                visibility = data.get("visibility", "public")
                is_public = (visibility == "public")

                created_at_str = data.get("created_at")
                created_at = None
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                if not posted_url:
                    return self.create_failed_result("Mastodon response did not include a status URL.")

                return self.create_success_result(
                    posted_url=posted_url,
                    public_access=is_public,
                    created_at=created_at,
                )

            except httpx.TimeoutException:
                return self.create_failed_result("Request to Mastodon API timed out.")
            except httpx.NetworkError as exc:
                return self.create_failed_result(f"Network error communicating with Mastodon instance: {exc}")
            except Exception as exc:
                logger.exception("Unexpected error during Mastodon publishing.")
                return self.create_failed_result(f"Unexpected error: {str(exc)}")
