"""Unit and integration tests for individual platform adapters."""

import pytest
import respx
from httpx import Response
from app.config import settings
from app.platforms.bluesky import BlueskyAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.telegram import TelegramAdapter
from app.platforms.discord import DiscordAdapter
from app.platforms.reddit import RedditAdapter
from app.schemas import PlatformPublishStatus


@pytest.fixture(autouse=True)
def mock_platform_env(monkeypatch):
    """Configure mock credentials for all adapters."""
    monkeypatch.setattr(settings, "BLUESKY_HANDLE", "alice.bsky.social")
    monkeypatch.setattr(settings, "BLUESKY_APP_PASSWORD", "mock-app-pass")
    monkeypatch.setattr(settings, "BLUESKY_PDS_URL", "https://bsky.social")

    monkeypatch.setattr(settings, "MASTODON_INSTANCE_URL", "https://mastodon.social")
    monkeypatch.setattr(settings, "MASTODON_ACCESS_TOKEN", "mock-mastodon-token")

    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setattr(settings, "TELEGRAM_CHAT_ID", "@nexus_channel")

    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/token_abc")

    monkeypatch.setattr(settings, "REDDIT_CLIENT_ID", "mock_client_id")
    monkeypatch.setattr(settings, "REDDIT_CLIENT_SECRET", "mock_client_secret")
    monkeypatch.setattr(settings, "REDDIT_USERNAME", "mock_user")
    monkeypatch.setattr(settings, "REDDIT_PASSWORD", "mock_password")
    monkeypatch.setattr(settings, "REDDIT_SUBREDDIT", "test")


class TestPlatformAdapters:
    """Test suite verifying each platform adapter handles success, failure, rate limits, and network errors."""

    # --------------------------------------------------------------------------
    # Bluesky Tests
    # --------------------------------------------------------------------------
    @pytest.mark.asyncio
    @respx.mock
    async def test_bluesky_success(self):
        adapter = BlueskyAdapter()

        # Mock session creation
        respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
            return_value=Response(
                200,
                json={"accessJwt": "jwt_token_123", "did": "did:plc:alice123", "handle": "alice.bsky.social"},
            )
        )
        # Mock record creation
        respx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord").mock(
            return_value=Response(
                200,
                json={"uri": "at://did:plc:alice123/app.bsky.feed.post/3k123456789", "cid": "bafy123"},
            )
        )

        result = await adapter.publish("Hello Bluesky https://example.com")
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.platform == "Bluesky"
        assert result.posted_url == "https://bsky.app/profile/alice.bsky.social/post/3k123456789"
        assert result.public_access is True
        assert result.error is None
        assert result.date is not None
        assert result.time is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_bluesky_auth_failure(self):
        adapter = BlueskyAdapter()
        respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
            return_value=Response(401, text="Invalid identifier or password")
        )

        result = await adapter.publish("Hello Bluesky https://example.com")
        assert result.status == PlatformPublishStatus.FAILED
        assert "Authentication failed" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_bluesky_rate_limited(self):
        adapter = BlueskyAdapter()
        respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
            return_value=Response(429, text="Rate limit exceeded")
        )

        result = await adapter.publish("Hello Bluesky https://example.com")
        assert result.status == PlatformPublishStatus.FAILED
        assert "rate limit exceeded" in result.error.lower()

    # --------------------------------------------------------------------------
    # Mastodon Tests
    # --------------------------------------------------------------------------
    @pytest.mark.asyncio
    @respx.mock
    async def test_mastodon_success(self):
        adapter = MastodonAdapter()
        respx.post("https://mastodon.social/api/v1/statuses").mock(
            return_value=Response(
                200,
                json={
                    "id": "10987654321",
                    "created_at": "2026-11-17T12:00:00.000Z",
                    "url": "https://mastodon.social/@nexus/10987654321",
                    "visibility": "public",
                },
            )
        )

        result = await adapter.publish("Hello Mastodon https://example.com")
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.platform == "Mastodon"
        assert result.posted_url == "https://mastodon.social/@nexus/10987654321"
        assert result.public_access is True
        assert result.error is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_mastodon_auth_failure(self):
        adapter = MastodonAdapter()
        respx.post("https://mastodon.social/api/v1/statuses").mock(
            return_value=Response(401, json={"error": "The access token is invalid"})
        )

        result = await adapter.publish("Hello Mastodon https://example.com")
        assert result.status == PlatformPublishStatus.FAILED
        assert "Authentication failed" in result.error

    # --------------------------------------------------------------------------
    # Telegram Tests
    # --------------------------------------------------------------------------
    @pytest.mark.asyncio
    @respx.mock
    async def test_telegram_public_channel_success(self):
        adapter = TelegramAdapter()
        respx.post("https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage").mock(
            return_value=Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "message_id": 999,
                        "chat": {"id": -1001234567, "username": "nexus_channel"},
                    },
                },
            )
        )

        result = await adapter.publish("Hello Telegram https://example.com")
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.posted_url == "https://t.me/nexus_channel/999"
        assert result.public_access is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_telegram_private_chat_success_no_public_url(self):
        adapter = TelegramAdapter()
        respx.post("https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage").mock(
            return_value=Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "message_id": 555,
                        "chat": {"id": 12345678},  # Private user chat without username
                    },
                },
            )
        )

        result = await adapter.publish("Hello Telegram https://example.com")
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.posted_url is None
        assert result.public_access is False

    # --------------------------------------------------------------------------
    # Discord Tests
    # --------------------------------------------------------------------------
    @pytest.mark.asyncio
    @respx.mock
    async def test_discord_success(self):
        adapter = DiscordAdapter()
        respx.post("https://discord.com/api/webhooks/123/token_abc?wait=true").mock(
            return_value=Response(
                200,
                json={
                    "id": "112233445566",
                    "channel_id": "77889900",
                    "guild_id": "99887766",
                },
            )
        )

        result = await adapter.publish("Hello Discord https://example.com")
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.posted_url == "https://discord.com/channels/99887766/77889900/112233445566"
        assert result.public_access is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_discord_rate_limited(self):
        adapter = DiscordAdapter()
        respx.post("https://discord.com/api/webhooks/123/token_abc?wait=true").mock(
            return_value=Response(429, json={"message": "You are being rate limited."})
        )

        result = await adapter.publish("Hello Discord https://example.com")
        assert result.status == PlatformPublishStatus.FAILED
        assert "rate limit exceeded" in result.error.lower()

    # --------------------------------------------------------------------------
    # Reddit Tests
    # --------------------------------------------------------------------------
    @pytest.mark.asyncio
    @respx.mock
    async def test_reddit_success(self):
        adapter = RedditAdapter()
        # Mock token request
        respx.post("https://www.reddit.com/api/v1/access_token").mock(
            return_value=Response(200, json={"access_token": "mock_reddit_token", "token_type": "bearer"})
        )
        # Mock submit request
        respx.post("https://oauth.reddit.com/api/submit").mock(
            return_value=Response(
                200,
                json={
                    "json": {
                        "errors": [],
                        "data": {
                            "url": "https://www.reddit.com/r/test/comments/xyz123/test_title/",
                            "id": "t3_xyz123",
                        },
                    }
                },
            )
        )

        result = await adapter.publish("Hello Reddit https://example.com")
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.posted_url == "https://www.reddit.com/r/test/comments/xyz123/test_title/"
        assert result.public_access is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_reddit_auth_failure(self):
        adapter = RedditAdapter()
        respx.post("https://www.reddit.com/api/v1/access_token").mock(
            return_value=Response(401, json={"error": "invalid_grant"})
        )

        result = await adapter.publish("Hello Reddit https://example.com")
        assert result.status == PlatformPublishStatus.FAILED
        assert "Authentication failed" in result.error

    # --------------------------------------------------------------------------
    # Unconfigured tests
    # --------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_unconfigured_adapters(self, monkeypatch):
        monkeypatch.setattr(settings, "BLUESKY_HANDLE", None)
        monkeypatch.setattr(settings, "MASTODON_INSTANCE_URL", None)
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
        monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", None)
        monkeypatch.setattr(settings, "REDDIT_CLIENT_ID", None)

        for AdapterClass in [BlueskyAdapter, MastodonAdapter, TelegramAdapter, DiscordAdapter, RedditAdapter]:
            adapter = AdapterClass()
            assert adapter.is_configured() is False
            res = await adapter.publish("Test message https://example.com")
            assert res.status == PlatformPublishStatus.UNCONFIGURED
            assert res.posted_url is None
            assert "unconfigured" in res.error.lower()
