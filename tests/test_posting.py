"""Integration tests for POST /posting endpoint and PostingService orchestration."""

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.config import settings
from app.main import app
from app.schemas import OverallStatus, PlatformPublishStatus


@pytest.fixture(autouse=True)
def mock_all_platform_env(monkeypatch):
    """Ensure platform credentials are fully configured for integration tests."""
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


class TestPostingIntegration:
    """Test suite covering end-to-end HTTP requests to /posting endpoint."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_all_platforms_succeed(self):
        # Bluesky mocks
        respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
            return_value=Response(
                200, json={"accessJwt": "jwt123", "did": "did:plc:alice", "handle": "alice.bsky.social"}
            )
        )
        respx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord").mock(
            return_value=Response(200, json={"uri": "at://did:plc:alice/app.bsky.feed.post/12345"})
        )
        # Mastodon mock
        respx.post("https://mastodon.social/api/v1/statuses").mock(
            return_value=Response(200, json={"url": "https://mastodon.social/@nexus/123", "visibility": "public"})
        )
        # Telegram mock
        respx.post("https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage").mock(
            return_value=Response(
                200, json={"ok": True, "result": {"message_id": 101, "chat": {"username": "nexus_channel"}}}
            )
        )
        # Discord mock
        respx.post("https://discord.com/api/webhooks/123/token_abc?wait=true").mock(
            return_value=Response(200, json={"id": "msg999", "channel_id": "ch1", "guild_id": "g1"})
        )
        # Reddit mock
        respx.post("https://www.reddit.com/api/v1/access_token").mock(
            return_value=Response(200, json={"access_token": "token_red"})
        )
        respx.post("https://oauth.reddit.com/api/submit").mock(
            return_value=Response(200, json={"json": {"errors": [], "data": {"url": "https://reddit.com/r/test/comments/123"}}})
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/posting",
                json={"message": "Announcing our new platform launch! https://nexus.example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["overall_status"] == OverallStatus.ALL_SUCCESS.value
        assert len(data["results"]) == 5

        for res in data["results"]:
            assert res["status"] == PlatformPublishStatus.SUCCESS.value
            assert res["date"] is not None
            assert res["time"] is not None
            assert res["error"] is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_partial_success_when_one_platform_fails(self):
        """Failure on Mastodon must not cancel or fail Bluesky, Telegram, Discord, or Reddit."""
        # Bluesky succeeds
        respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
            return_value=Response(
                200, json={"accessJwt": "jwt123", "did": "did:plc:alice", "handle": "alice.bsky.social"}
            )
        )
        respx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord").mock(
            return_value=Response(200, json={"uri": "at://did:plc:alice/app.bsky.feed.post/12345"})
        )
        # Mastodon fails with 401
        respx.post("https://mastodon.social/api/v1/statuses").mock(
            return_value=Response(401, json={"error": "The access token is invalid"})
        )
        # Telegram succeeds
        respx.post("https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage").mock(
            return_value=Response(
                200, json={"ok": True, "result": {"message_id": 101, "chat": {"username": "nexus_channel"}}}
            )
        )
        # Discord succeeds
        respx.post("https://discord.com/api/webhooks/123/token_abc?wait=true").mock(
            return_value=Response(200, json={"id": "msg999", "channel_id": "ch1", "guild_id": "g1"})
        )
        # Reddit succeeds
        respx.post("https://www.reddit.com/api/v1/access_token").mock(
            return_value=Response(200, json={"access_token": "token_red"})
        )
        respx.post("https://oauth.reddit.com/api/submit").mock(
            return_value=Response(200, json={"json": {"errors": [], "data": {"url": "https://reddit.com/r/test/comments/123"}}})
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/posting",
                json={"message": "Announcing our new platform launch! https://nexus.example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["overall_status"] == OverallStatus.PARTIAL_SUCCESS.value
        assert len(data["results"]) == 5

        # Verify Mastodon failed while others succeeded
        masto_result = next(r for r in data["results"] if r["platform"] == "Mastodon")
        assert masto_result["status"] == PlatformPublishStatus.FAILED.value
        assert "Authentication failed" in masto_result["error"]
        assert masto_result["posted_url"] is None

        bsky_result = next(r for r in data["results"] if r["platform"] == "Bluesky")
        assert bsky_result["status"] == PlatformPublishStatus.SUCCESS.value

    @pytest.mark.asyncio
    @respx.mock
    async def test_all_platforms_fail(self):
        """When all platforms encounter errors, overall_status is all_failed."""
        respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
            return_value=Response(500, text="Internal Server Error")
        )
        respx.post("https://mastodon.social/api/v1/statuses").mock(
            return_value=Response(503, text="Service Unavailable")
        )
        respx.post("https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage").mock(
            return_value=Response(400, json={"ok": False, "description": "Chat not found"})
        )
        respx.post("https://discord.com/api/webhooks/123/token_abc?wait=true").mock(
            return_value=Response(404, json={"message": "Unknown Webhook"})
        )
        respx.post("https://www.reddit.com/api/v1/access_token").mock(
            return_value=Response(401, json={"error": "invalid_grant"})
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/posting",
                json={"message": "Check our service: https://nexus.example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["overall_status"] == OverallStatus.ALL_FAILED.value
        for r in data["results"]:
            assert r["status"] == PlatformPublishStatus.FAILED.value
            assert r["error"] is not None

    @pytest.mark.asyncio
    async def test_no_platforms_configured(self, monkeypatch):
        """When all environment variables are unconfigured."""
        monkeypatch.setattr(settings, "BLUESKY_HANDLE", None)
        monkeypatch.setattr(settings, "MASTODON_INSTANCE_URL", None)
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
        monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", None)
        monkeypatch.setattr(settings, "REDDIT_CLIENT_ID", None)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/posting",
                json={"message": "Check our service: https://nexus.example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["overall_status"] == OverallStatus.NO_PLATFORMS_CONFIGURED.value
        for r in data["results"]:
            assert r["status"] == PlatformPublishStatus.UNCONFIGURED.value

    @pytest.mark.asyncio
    async def test_validation_error_returns_422(self):
        """Invalid requests (e.g. missing URL or > 200 chars) return HTTP 422 with useful error messages."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Missing URL
            resp1 = await ac.post("/posting", json={"message": "This message has no URL at all."})
            assert resp1.status_code == 422
            assert "exactly one valid HTTP or HTTPS URL" in resp1.json()["detail"]

            # 2. Empty message
            resp2 = await ac.post("/posting", json={"message": ""})
            assert resp2.status_code == 422
            assert "empty or contain only whitespace" in resp2.json()["detail"]

            # 3. Message exceeds 200 chars
            long_msg = "X" * 185 + " https://example.com"
            resp3 = await ac.post("/posting", json={"message": long_msg})
            assert resp3.status_code == 422
            assert "exceeds the maximum allowed limit of 200" in resp3.json()["detail"]

    @pytest.mark.asyncio
    async def test_system_endpoints(self):
        """Verify GET /, GET /health, and GET /platforms."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Root
            r_root = await ac.get("/")
            assert r_root.status_code == 200
            assert r_root.json()["project"] == "NEXUS"

            # Health
            r_health = await ac.get("/health")
            assert r_health.status_code == 200
            assert r_health.json()["status"] == "healthy"
            assert r_health.json()["total_platforms_count"] == 5

            # Platforms
            r_plat = await ac.get("/platforms")
            assert r_plat.status_code == 200
            assert r_plat.json()["total_platforms"] == 5
            names = [p["platform"] for p in r_plat.json()["platforms"]]
            assert set(names) == {"Bluesky", "Mastodon", "Telegram", "Discord", "Reddit"}
