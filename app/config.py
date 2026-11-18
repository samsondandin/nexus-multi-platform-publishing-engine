"""Application configuration module loaded via Pydantic Settings."""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """NEXUS core application, LLM, and platform settings."""

    # Server Settings (default 4000 locally, or uses $PORT injected by Cloud Run / environment)
    PORT: int = int(os.getenv("PORT", "4000"))
    HOST: str = "0.0.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    MAX_RETRIES: int = 2

    # LLM Providers Configuration
    DEFAULT_LLM_PROVIDER: str = "gemini"
    DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: Optional[str] = None

    OPENAI_API_KEY: Optional[str] = None
    DEFAULT_OPENAI_MODEL: str = "gpt-4o-mini"

    GROQ_API_KEY: Optional[str] = None
    DEFAULT_GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Social Publishing Platforms
    # Bluesky (AT Protocol)
    BLUESKY_HANDLE: Optional[str] = None
    BLUESKY_APP_PASSWORD: Optional[str] = None
    BLUESKY_PDS_URL: str = "https://bsky.social"

    # Mastodon (REST API)
    MASTODON_INSTANCE_URL: Optional[str] = None
    MASTODON_ACCESS_TOKEN: Optional[str] = None

    # Telegram (Bot API)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Discord (Webhook API)
    DISCORD_WEBHOOK_URL: Optional[str] = None

    # Reddit (OAuth2 Script App)
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USERNAME: Optional[str] = None
    REDDIT_PASSWORD: Optional[str] = None
    REDDIT_USER_AGENT: str = "nexus-publishing-engine/1.0"
    REDDIT_SUBREDDIT: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
