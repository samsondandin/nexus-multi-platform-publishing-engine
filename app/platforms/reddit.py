"""Reddit OAuth2 API platform adapter."""

import httpx
from app.config import settings
from app.platforms.base import BasePlatformAdapter
from app.schemas import PlatformResult
from app.utils.logging import logger


class RedditAdapter(BasePlatformAdapter):
    """Adapter for Reddit using the official OAuth2 API (POST /api/submit).

    API Flow:
    1. Authenticate with https://www.reddit.com/api/v1/access_token using HTTP Basic Auth
       (client_id:client_secret) and password grant (username & password).
    2. Obtain Bearer access_token.
    3. Send POST https://oauth.reddit.com/api/submit with:
       - sr: target subreddit
       - kind: 'self'
       - title: first 80 chars of message
       - text: message
       - resubmit: true
    4. Reddit returns JSON containing `json.data.url` (e.g. https://www.reddit.com/r/sub/comments/id/title/).
    5. Return normalized PlatformResult with public_access=True.
    """

    @property
    def platform_name(self) -> str:
        return "Reddit"

    @property
    def public_access_supported(self) -> bool:
        return True

    @property
    def docs_url(self) -> str:
        return "https://www.reddit.com/dev/api#POST_api_submit"

    @property
    def description(self) -> str:
        return "Social news aggregation and discussion platform via the Reddit OAuth2 API."

    def is_configured(self) -> bool:
        return bool(
            settings.REDDIT_CLIENT_ID
            and settings.REDDIT_CLIENT_SECRET
            and settings.REDDIT_USERNAME
            and settings.REDDIT_PASSWORD
            and settings.REDDIT_SUBREDDIT
        )

    async def publish(self, message: str) -> PlatformResult:
        if not self.is_configured():
            return self.create_unconfigured_result()

        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS)
        user_agent = settings.REDDIT_USER_AGENT

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                # 1. Obtain OAuth2 Token
                token_auth = (settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET)
                token_data = {
                    "grant_type": "password",
                    "username": settings.REDDIT_USERNAME,
                    "password": settings.REDDIT_PASSWORD,
                }
                token_headers = {"User-Agent": user_agent}

                token_resp = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    auth=token_auth,
                    data=token_data,
                    headers=token_headers,
                )

                if token_resp.status_code == 401:
                    return self.create_failed_result("Authentication failed: Invalid Reddit client credentials.")
                elif token_resp.is_error:
                    return self.create_failed_result(
                        f"Reddit authentication error (HTTP {token_resp.status_code}): {token_resp.text}"
                    )

                token_json = token_resp.json()
                access_token = token_json.get("access_token")
                if not access_token:
                    error_desc = token_json.get("error", "Unknown token error")
                    return self.create_failed_result(f"Failed to obtain Reddit access token: {error_desc}")

                # 2. Submit Post
                # Use title derived from message (up to 80 chars)
                title = message[:80].strip()
                submit_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": user_agent,
                }
                submit_payload = {
                    "api_type": "json",
                    "sr": settings.REDDIT_SUBREDDIT,
                    "kind": "self",
                    "title": title,
                    "text": message,
                    "resubmit": "true",
                }

                submit_resp = await client.post(
                    "https://oauth.reddit.com/api/submit",
                    headers=submit_headers,
                    data=submit_payload,
                )

                if submit_resp.status_code == 403:
                    return self.create_failed_result(
                        f"Permission denied: Unable to post to subreddit 'r/{settings.REDDIT_SUBREDDIT}'."
                    )
                elif submit_resp.status_code == 429:
                    return self.create_failed_result("Reddit rate limit exceeded (HTTP 429).")
                elif submit_resp.is_error:
                    return self.create_failed_result(
                        f"Reddit submission error (HTTP {submit_resp.status_code}): {submit_resp.text}"
                    )

                submit_json = submit_resp.json()
                errors = submit_json.get("json", {}).get("errors", [])
                if errors:
                    err_msg = "; ".join([str(e) for e in errors])
                    return self.create_failed_result(f"Reddit API rejected submission: {err_msg}")

                posted_url = submit_json.get("json", {}).get("data", {}).get("url")
                if not posted_url:
                    return self.create_failed_result("Reddit response did not include a submission URL.")

                return self.create_success_result(
                    posted_url=posted_url,
                    public_access=True,
                )

            except httpx.TimeoutException:
                return self.create_failed_result("Request to Reddit API timed out.")
            except httpx.NetworkError as exc:
                return self.create_failed_result(f"Network error communicating with Reddit: {exc}")
            except Exception as exc:
                logger.exception("Unexpected error during Reddit publishing.")
                return self.create_failed_result(f"Unexpected error: {str(exc)}")
