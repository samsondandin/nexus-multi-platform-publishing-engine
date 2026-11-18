"""LLM Provider Manager and factory."""

from typing import Optional

from app.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.gemini import GeminiProvider
from app.services.llm.openai import OpenAIProvider


class LLMService:
    """Manages LLM providers, routing requests and handling fallbacks."""

    def get_provider(self, name: Optional[str] = None) -> BaseLLMProvider:
        """Get an active LLM provider by name or fallback to default configured provider."""
        provider_name = (name or settings.DEFAULT_LLM_PROVIDER).lower().strip()
        if provider_name == "openai":
            return OpenAIProvider()
        return GeminiProvider()

    def is_any_configured(self) -> bool:
        """Check if at least one LLM provider has credentials set."""
        return GeminiProvider().is_configured() or OpenAIProvider().is_configured()


llm_service = LLMService()
