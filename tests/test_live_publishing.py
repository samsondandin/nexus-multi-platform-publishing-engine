"""Live external integration tests for NEXUS publishing engine.

WARNING: These tests execute REAL API calls against live third-party platforms
and require active environment credentials. They are skipped by default during normal test runs.

To run:
    pytest tests/test_live_publishing.py --run-live
"""

import pytest

from app.platforms.bluesky import BlueskyAdapter
from app.platforms.discord import DiscordAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.reddit import RedditAdapter
from app.platforms.telegram import TelegramAdapter
from app.schemas import PlatformPublishStatus


def is_live_opted_in(request: pytest.FixtureRequest) -> bool:
    return request.config.getoption("--run-live", default=False)


@pytest.fixture
def check_live(request: pytest.FixtureRequest):
    if not is_live_opted_in(request):
        pytest.skip("Skipping live integration tests. Opt-in with '--run-live'.")


class TestLivePublishing:
    """Live publishing tests against genuine external platforms when configured."""

    @pytest.mark.asyncio
    async def test_live_bluesky_publish(self, check_live):
        adapter = BlueskyAdapter()
        if not adapter.is_configured():
            pytest.skip("Bluesky credentials not configured in environment.")

        msg = "NEXUS live engine test https://nexus.example.com"
        result = await adapter.publish(msg)
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.posted_url is not None
        assert "bsky.app" in result.posted_url

    @pytest.mark.asyncio
    async def test_live_mastodon_publish(self, check_live):
        adapter = MastodonAdapter()
        if not adapter.is_configured():
            pytest.skip("Mastodon credentials not configured in environment.")

        msg = "NEXUS live engine test https://nexus.example.com"
        result = await adapter.publish(msg)
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.posted_url is not None

    @pytest.mark.asyncio
    async def test_live_telegram_publish(self, check_live):
        adapter = TelegramAdapter()
        if not adapter.is_configured():
            pytest.skip("Telegram credentials not configured in environment.")

        msg = "NEXUS live engine test https://nexus.example.com"
        result = await adapter.publish(msg)
        assert result.status == PlatformPublishStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_live_discord_publish(self, check_live):
        adapter = DiscordAdapter()
        if not adapter.is_configured():
            pytest.skip("Discord webhook not configured in environment.")

        msg = "NEXUS live engine test https://nexus.example.com"
        result = await adapter.publish(msg)
        assert result.status == PlatformPublishStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_live_reddit_publish(self, check_live):
        adapter = RedditAdapter()
        if not adapter.is_configured():
            pytest.skip("Reddit credentials not configured in environment.")

        msg = "NEXUS live engine test https://nexus.example.com"
        result = await adapter.publish(msg)
        assert result.status == PlatformPublishStatus.SUCCESS
        assert result.posted_url is not None
