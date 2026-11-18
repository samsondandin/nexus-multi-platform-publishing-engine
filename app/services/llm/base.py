"""Base LLM Provider abstract interface and cost estimation contracts."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from app.schemas import LinkAnalysisResponse


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM providers generating structured link analysis."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier (e.g. 'gemini', 'openai', 'groq')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model identifier (e.g. 'gemini-2.5-flash')."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if required API keys are configured."""
        pass

    @abstractmethod
    async def analyze_website_content(
        self,
        url: str,
        scraped_data: Dict[str, Optional[str]],
    ) -> LinkAnalysisResponse:
        """Analyze scraped website content and produce structured LinkAnalysisResponse."""
        pass

    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD based on official token pricing."""
        pass
