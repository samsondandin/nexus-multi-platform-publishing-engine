"""Publishing orchestration service with concurrent execution and failure isolation."""

import asyncio
from typing import List, Sequence
from app.platforms.base import BasePlatformAdapter
from app.platforms.bluesky import BlueskyAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.telegram import TelegramAdapter
from app.platforms.discord import DiscordAdapter
from app.platforms.reddit import RedditAdapter
from app.schemas import (
    OverallStatus,
    PlatformPublishStatus,
    PlatformResult,
    PostingResponse,
    PlatformInfo,
)
from app.utils.logging import logger


class PostingService:
    """Orchestrates multi-platform publishing with full isolation, concurrency, and response normalization."""

    def __init__(self, adapters: Sequence[BasePlatformAdapter] | None = None):
        """Initialize the posting service with adapters. Defaults to the 5 core platforms."""
        if adapters is not None:
            self._adapters = list(adapters)
        else:
            self._adapters = [
                BlueskyAdapter(),
                MastodonAdapter(),
                TelegramAdapter(),
                DiscordAdapter(),
                RedditAdapter(),
            ]

    @property
    def adapters(self) -> List[BasePlatformAdapter]:
        return self._adapters

    def get_platforms_info(self) -> List[PlatformInfo]:
        """Return operational metadata for all registered adapters."""
        return [
            PlatformInfo(
                platform=adapter.platform_name,
                configured=adapter.is_configured(),
                public_access_supported=adapter.public_access_supported,
                description=adapter.description,
                docs_url=adapter.docs_url,
            )
            for adapter in self._adapters
        ]

    async def _publish_single_adapter(
        self, adapter: BasePlatformAdapter, message: str
    ) -> PlatformResult:
        """Safely execute publishing on a single adapter with absolute fault isolation."""
        try:
            return await adapter.publish(message)
        except Exception as exc:
            logger.exception("Unhandled exception in platform adapter %s", adapter.platform_name)
            return adapter.create_failed_result(f"Adapter internal error: {str(exc)}")

    async def publish_message(self, message: str) -> PostingResponse:
        """Publish a validated message across all registered platforms concurrently.

        Guarantees:
        - Independent execution: failure on one platform never blocks or cancels others.
        - Concurrency via asyncio.gather().
        - Deterministic results: returns exact status for every attempted platform.
        - Calculated overall_status and success flag.
        """
        logger.info("Initiating multi-platform publishing for message (%d chars).", len(message))

        # Run all adapters concurrently with gather; return_exceptions ensures all finish
        tasks = [self._publish_single_adapter(adapter, message) for adapter in self._adapters]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Compute summary metrics
        total = len(results)
        successes = sum(1 for r in results if r.status == PlatformPublishStatus.SUCCESS)
        failures = sum(1 for r in results if r.status == PlatformPublishStatus.FAILED)
        unconfigured = sum(1 for r in results if r.status == PlatformPublishStatus.UNCONFIGURED)

        configured_count = total - unconfigured

        if configured_count == 0:
            overall_status = OverallStatus.NO_PLATFORMS_CONFIGURED
            success = False
        elif successes == configured_count:
            overall_status = OverallStatus.ALL_SUCCESS
            success = True
        elif successes > 0:
            overall_status = OverallStatus.PARTIAL_SUCCESS
            success = False
        else:
            overall_status = OverallStatus.ALL_FAILED
            success = False

        logger.info(
            "Publishing completed: %d total, %d success, %d failed, %d unconfigured. Overall: %s",
            total,
            successes,
            failures,
            unconfigured,
            overall_status.value,
        )

        return PostingResponse(
            success=success,
            overall_status=overall_status,
            results=results,
        )


# Singleton instance for route injection
posting_service = PostingService()
