"""Base platform adapter contract and normalized execution result."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from app.schemas import PlatformPublishStatus, PlatformResult
from app.utils.logging import logger


class BasePlatformAdapter(ABC):
    """Abstract Base Class for all NEXUS publishing platform adapters.

    Every platform adapter must:
    1. Define a human-readable platform_name.
    2. Provide an is_configured() method to verify required environment credentials.
    3. Implement async publish(message: str) to post content via genuine APIs.
    4. Provide normalized responses and error handling without crashing or leaking secrets.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the unique human-readable name of the platform."""
        pass

    @property
    @abstractmethod
    def public_access_supported(self) -> bool:
        """Return True if posts on this platform are publicly viewable without authentication."""
        pass

    @property
    @abstractmethod
    def docs_url(self) -> str:
        """Return the official API documentation URL for this platform."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a brief description of the platform adapter."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if all required configuration parameters/credentials are present."""
        pass

    @abstractmethod
    async def publish(self, message: str) -> PlatformResult:
        """Publish a validated message to the platform via genuine HTTP API calls.

        Args:
            message: The validated text content containing exactly one URL.

        Returns:
            PlatformResult: Normalized result containing status, posted URL, timestamp, and errors.
        """
        pass

    @staticmethod
    def current_utc_timestamps() -> tuple[str, str]:
        """Return current UTC date (YYYY-MM-DD) and time (HH:MM:SS)."""
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    def create_unconfigured_result(self) -> PlatformResult:
        """Standardized result returned when a platform adapter is not configured."""
        logger.info("Platform %s is not configured (missing credentials).", self.platform_name)
        return PlatformResult(
            platform=self.platform_name,
            status=PlatformPublishStatus.UNCONFIGURED,
            posted_url=None,
            public_access=None,
            date=None,
            time=None,
            error=f"{self.platform_name} adapter is unconfigured: missing credentials in environment variables.",
        )

    def create_failed_result(self, error_message: str) -> PlatformResult:
        """Standardized result returned when a publishing attempt fails."""
        date_str, time_str = self.current_utc_timestamps()
        logger.error("Platform %s publishing failed: %s", self.platform_name, error_message)
        return PlatformResult(
            platform=self.platform_name,
            status=PlatformPublishStatus.FAILED,
            posted_url=None,
            public_access=None,
            date=date_str,
            time=time_str,
            error=error_message,
        )

    def create_success_result(
        self,
        posted_url: str,
        public_access: bool,
        created_at: Optional[datetime] = None,
    ) -> PlatformResult:
        """Standardized result returned when publishing succeeds."""
        if created_at is not None:
            utc_dt = created_at.astimezone(timezone.utc)
            date_str = utc_dt.strftime("%Y-%m-%d")
            time_str = utc_dt.strftime("%H:%M:%S")
        else:
            date_str, time_str = self.current_utc_timestamps()

        logger.info("Platform %s publishing succeeded. Post URL: %s", self.platform_name, posted_url)
        return PlatformResult(
            platform=self.platform_name,
            status=PlatformPublishStatus.SUCCESS,
            posted_url=posted_url,
            public_access=public_access,
            date=date_str,
            time=time_str,
            error=None,
        )
