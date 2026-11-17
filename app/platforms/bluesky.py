"""Bluesky (AT Protocol) platform adapter."""

from datetime import datetime, timezone

import httpx

from app.config import settings
from app.platforms.base import BasePlatformAdapter
from app.schemas import PlatformResult
from app.utils.logging import logger


class BlueskyAdapter(BasePlatformAdapter):
    """Adapter for Bluesky using the official AT Protocol HTTP API (com.atproto).

    API Flow:
    1. Authenticate via com.atproto.server.createSession using handle and app password.
    2. Extract accessJwt and DID from response.
    3. Publish post record via com.atproto.repo.createRecord into collection 'app.bsky.feed.post'.
    4. Compute public post URL: https://bsky.app/profile/{handle}/post/{rkey}.
    5. Return normalized PlatformResult.
    """

    @property
    def platform_name(self) -> str:
        return "Bluesky"

    @property
    def public_access_supported(self) -> bool:
        return True

    @property
    def docs_url(self) -> str:
        return "https://docs.bsky.app/docs/category/http-reference"

    @property
    def description(self) -> str:
        return "Decentralized social network powered by the AT Protocol."

    def is_configured(self) -> bool:
        return bool(settings.BLUESKY_HANDLE and settings.BLUESKY_APP_PASSWORD)

    async def publish(self, message: str) -> PlatformResult:
        if not self.is_configured():
            return self.create_unconfigured_result()

        pds_url = settings.BLUESKY_PDS_URL.rstrip("/")
        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                # 1. Create Session
                session_resp = await client.post(
                    f"{pds_url}/xrpc/com.atproto.server.createSession",
                    json={
                        "identifier": settings.BLUESKY_HANDLE,
                        "password": settings.BLUESKY_APP_PASSWORD,
                    },
                )

                if session_resp.status_code == 401:
                    return self.create_failed_result("Authentication failed: Invalid Bluesky handle or app password.")
                elif session_resp.status_code == 429:
                    return self.create_failed_result("Bluesky rate limit exceeded (HTTP 429).")
                elif session_resp.is_error:
                    return self.create_failed_result(
                        f"Bluesky session creation error (HTTP {session_resp.status_code}): {session_resp.text}"
                    )

                session_data = session_resp.json()
                access_jwt = session_data.get("accessJwt")
                user_did = session_data.get("did")
                user_handle = session_data.get("handle", settings.BLUESKY_HANDLE)

                if not access_jwt or not user_did:
                    return self.create_failed_result("Malformed session response from Bluesky PDS.")

                # 2. Create Post Record
                now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                headers = {"Authorization": f"Bearer {access_jwt}"}
                post_payload = {
                    "repo": user_did,
                    "collection": "app.bsky.feed.post",
                    "record": {
                        "$type": "app.bsky.feed.post",
                        "text": message,
                        "createdAt": now_iso,
                    },
                }

                post_resp = await client.post(
                    f"{pds_url}/xrpc/com.atproto.repo.createRecord",
                    headers=headers,
                    json=post_payload,
                )

                if post_resp.status_code == 429:
                    return self.create_failed_result("Bluesky rate limit exceeded while creating record (HTTP 429).")
                elif post_resp.is_error:
                    return self.create_failed_result(
                        f"Bluesky post creation error (HTTP {post_resp.status_code}): {post_resp.text}"
                    )

                post_data = post_resp.json()
                uri = post_data.get("uri")  # Format: at://did:plc:xxx/app.bsky.feed.post/rkey

                if not uri:
                    return self.create_failed_result("Bluesky did not return a post URI in the response.")

                # Extract rkey from AT URI
                rkey = uri.rstrip("/").split("/")[-1]
                posted_url = f"https://bsky.app/profile/{user_handle}/post/{rkey}"

                return self.create_success_result(posted_url=posted_url, public_access=True)

            except httpx.TimeoutException:
                return self.create_failed_result("Request to Bluesky API timed out.")
            except httpx.NetworkError as exc:
                return self.create_failed_result(f"Network error communicating with Bluesky: {exc}")
            except Exception as exc:
                logger.exception("Unexpected error during Bluesky publishing.")
                return self.create_failed_result(f"Unexpected error: {str(exc)}")
