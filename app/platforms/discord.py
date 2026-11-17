"""Discord Webhook platform adapter."""

import httpx
from app.config import settings
from app.platforms.base import BasePlatformAdapter
from app.schemas import PlatformResult
from app.utils.logging import logger


class DiscordAdapter(BasePlatformAdapter):
    """Adapter for Discord using official Execute Webhook API (POST /api/webhooks/{id}/{token}?wait=true).

    API Flow:
    1. Send POST request to configured Discord Webhook URL with `?wait=true` to receive message entity.
    2. Payload contains `content`.
    3. Discord returns HTTP 200 with Message object containing `id`, `channel_id`, `guild_id`.
    4. Discord messages in server channels require authentication/membership, so public_access is False.
       Post jump URL: https://discord.com/channels/{guild_id}/{channel_id}/{id}.
    5. Return normalized PlatformResult.
    """

    @property
    def platform_name(self) -> str:
        return "Discord"

    @property
    def public_access_supported(self) -> bool:
        # Discord messages require server membership/login to view
        return False

    @property
    def docs_url(self) -> str:
        return "https://discord.com/developers/docs/resources/webhook#execute-webhook"

    @property
    def description(self) -> str:
        return "Community messaging platform using official Discord Execute Webhook API."

    def is_configured(self) -> bool:
        return bool(settings.DISCORD_WEBHOOK_URL)

    async def publish(self, message: str) -> PlatformResult:
        if not self.is_configured():
            return self.create_unconfigured_result()

        webhook_url = settings.DISCORD_WEBHOOK_URL.strip()
        # Add ?wait=true parameter so Discord returns the created message JSON rather than 204 No Content
        delimiter = "&" if "?" in webhook_url else "?"
        target_url = f"{webhook_url}{delimiter}wait=true"

        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS)
        payload = {"content": message}

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(target_url, json=payload)

                if resp.status_code == 401 or resp.status_code == 404:
                    return self.create_failed_result("Authentication failed: Invalid or deleted Discord webhook URL.")
                elif resp.status_code == 429:
                    return self.create_failed_result("Discord rate limit exceeded (HTTP 429).")
                elif resp.is_error:
                    return self.create_failed_result(
                        f"Discord API error (HTTP {resp.status_code}): {resp.text}"
                    )

                data = resp.json()
                msg_id = data.get("id")
                channel_id = data.get("channel_id")
                guild_id = data.get("guild_id", "@me")

                if msg_id and channel_id:
                    posted_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
                else:
                    posted_url = None

                # Discord messages require an authenticated user in the guild/channel
                return self.create_success_result(
                    posted_url=posted_url,
                    public_access=False,
                )

            except httpx.TimeoutException:
                return self.create_failed_result("Request to Discord API timed out.")
            except httpx.NetworkError as exc:
                return self.create_failed_result(f"Network error communicating with Discord: {exc}")
            except Exception as exc:
                logger.exception("Unexpected error during Discord publishing.")
                return self.create_failed_result(f"Unexpected error: {str(exc)}")
