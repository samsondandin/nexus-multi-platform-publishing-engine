"""Telegram Bot API platform adapter."""

import httpx
from app.config import settings
from app.platforms.base import BasePlatformAdapter
from app.schemas import PlatformResult
from app.utils.logging import logger


class TelegramAdapter(BasePlatformAdapter):
    """Adapter for Telegram using the official Bot API (POST /bot<token>/sendMessage).

    API Flow:
    1. Send message to target chat/channel using `sendMessage`.
    2. Response contains `result` with `message_id`, `chat` object.
    3. If target is a public channel/supergroup with a username, the post URL is:
       https://t.me/{username}/{message_id}.
    4. If target is a private chat/group without a username, the post does not have a public URL.
       In that case, posted_url is None and public_access is False.
    5. Return normalized PlatformResult.
    """

    @property
    def platform_name(self) -> str:
        return "Telegram"

    @property
    def public_access_supported(self) -> bool:
        # Public access depends on whether the target channel has a public username
        return True

    @property
    def docs_url(self) -> str:
        return "https://core.telegram.org/bots/api#sendmessage"

    @property
    def description(self) -> str:
        return "Cloud-based messaging platform and broadcast channels via the Telegram Bot API."

    def is_configured(self) -> bool:
        return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)

    async def publish(self, message: str) -> PlatformResult:
        if not self.is_configured():
            return self.create_unconfigured_result()

        bot_token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS)

        api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": False,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(api_url, json=payload)

                if resp.status_code == 401:
                    return self.create_failed_result("Authentication failed: Invalid Telegram bot token.")
                elif resp.status_code == 400:
                    return self.create_failed_result(f"Bad Request to Telegram Bot API: {resp.text}")
                elif resp.status_code == 429:
                    return self.create_failed_result("Telegram rate limit exceeded (HTTP 429).")
                elif resp.is_error:
                    return self.create_failed_result(
                        f"Telegram API error (HTTP {resp.status_code}): {resp.text}"
                    )

                data = resp.json()
                if not data.get("ok"):
                    desc = data.get("description", "Unknown Telegram API error")
                    return self.create_failed_result(f"Telegram error: {desc}")

                result_obj = data.get("result", {})
                message_id = result_obj.get("message_id")
                chat = result_obj.get("chat", {})
                username = chat.get("username")

                # If channel or group has a public username, message is publicly accessible
                if username and message_id:
                    posted_url = f"https://t.me/{username}/{message_id}"
                    public_access = True
                else:
                    # Message sent to private chat or group without public username
                    posted_url = None
                    public_access = False

                return self.create_success_result(
                    posted_url=posted_url,
                    public_access=public_access,
                )

            except httpx.TimeoutException:
                return self.create_failed_result("Request to Telegram API timed out.")
            except httpx.NetworkError as exc:
                return self.create_failed_result(f"Network error communicating with Telegram: {exc}")
            except Exception as exc:
                logger.exception("Unexpected error during Telegram publishing.")
                return self.create_failed_result(f"Unexpected error: {str(exc)}")
