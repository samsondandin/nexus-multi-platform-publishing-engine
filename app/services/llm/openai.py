"""OpenAI LLM provider implementation for Link Analysis."""

import json
from typing import Dict, Optional

import httpx

from app.config import settings
from app.schemas import (
    CompetitorAnalysis,
    LinkAnalysisResponse,
    LLMMetadata,
    PlatformSearchQueries,
    SEORecommendations,
    ServiceItem,
    TargetAudience,
)
from app.services.llm.base import BaseLLMProvider
from app.services.llm.prompts import ANALYSIS_SYSTEM_INSTRUCTION, build_analysis_user_prompt


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API integration (gpt-4o-mini)."""

    # Pricing for GPT-4o-mini (USD per 1M tokens)
    # Input: $0.15 / 1M tokens
    # Output: $0.60 / 1M tokens
    INPUT_COST_PER_MILLION = 0.15
    OUTPUT_COST_PER_MILLION = 0.60

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.DEFAULT_OPENAI_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        input_cost = (prompt_tokens / 1_000_000.0) * self.INPUT_COST_PER_MILLION
        output_cost = (completion_tokens / 1_000_000.0) * self.OUTPUT_COST_PER_MILLION
        return round(input_cost + output_cost, 7)

    async def analyze_website_content(
        self,
        url: str,
        scraped_data: Dict[str, Optional[str]],
    ) -> LinkAnalysisResponse:
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured. Please set OPENAI_API_KEY.")

        endpoint = "https://api.openai.com/v1/chat/completions"
        user_prompt = build_analysis_user_prompt(url, scraped_data)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": ANALYSIS_SYSTEM_INSTRUCTION},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS * 2)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(endpoint, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                raise TimeoutError(f"OpenAI API call timed out after {timeout.read}s.") from exc
            except httpx.NetworkError as exc:
                raise ConnectionError(f"Network error communicating with OpenAI API: {exc}") from exc

            if response.status_code in (401, 403):
                raise PermissionError("Authentication failed: Invalid or unauthorized OPENAI_API_KEY.")
            elif response.status_code == 429:
                raise RuntimeError("OpenAI API rate limit exceeded (HTTP 429).")
            elif response.is_error:
                raise RuntimeError(f"OpenAI API error (HTTP {response.status_code}): {response.text}")

            result_json = response.json()

        usage = result_json.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(user_prompt) // 4)
        completion_tokens = usage.get("completion_tokens", 500)
        estimated_cost = self.calculate_cost(prompt_tokens, completion_tokens)

        choices = result_json.get("choices", [])
        if not choices:
            raise ValueError("OpenAI API returned an empty choices list.")

        raw_content = choices[0].get("message", {}).get("content", "").strip()
        parsed = json.loads(raw_content)

        raw_services = parsed.get("top_5_services", [])
        services_list = []
        for s in raw_services[:5]:
            if isinstance(s, dict):
                services_list.append(ServiceItem(name=s.get("name", "Service"), description=s.get("description", "")))
            elif isinstance(s, str):
                services_list.append(ServiceItem(name=s, description="Core service offering identified on website."))

        while len(services_list) < 5:
            idx = len(services_list) + 1
            services_list.append(
                ServiceItem(name=f"Consulting & Support Offering {idx}", description="Client advisory and operational support.")
            )

        target_aud = parsed.get("target_audience", {})
        comp_anal = parsed.get("competitor_analysis", {})
        search_q = parsed.get("target_search_queries", {})
        seo_imp = parsed.get("seo_improvements", {})

        return LinkAnalysisResponse(
            url=url,
            scraped_title=scraped_data.get("title"),
            scraped_description=scraped_data.get("meta_description"),
            top_5_services=services_list,
            target_audience=TargetAudience(
                primary_audience=target_aud.get("primary_audience", "Target businesses and digital buyers"),
                secondary_audience=target_aud.get("secondary_audience", "Enterprise organizations"),
                industry_verticals=target_aud.get("industry_verticals", ["Technology", "Digital Services"]),
            ),
            competitor_analysis=CompetitorAnalysis(
                direct_competitors=comp_anal.get("direct_competitors", ["Direct Competitor 1", "Direct Competitor 2"]),
                indirect_competitors=comp_anal.get("indirect_competitors", ["Indirect Alternative 1"]),
                competitive_advantage=comp_anal.get("competitive_advantage", "High performance and ease of integration."),
            ),
            target_search_queries=PlatformSearchQueries(
                google=search_q.get("google", [f"{url} services"]),
                facebook=search_q.get("facebook", ["recommended solutions"]),
                instagram=search_q.get("instagram", ["#techsolutions"]),
                linkedin=search_q.get("linkedin", ["B2B enterprise services"]),
                x=search_q.get("x", ["#techtools"]),
            ),
            seo_improvements=SEORecommendations(
                title_and_metadata=seo_imp.get("title_and_metadata", ["Optimize title tag length to 55 characters"]),
                content_and_keywords=seo_imp.get("content_and_keywords", ["Add descriptive keyword headings"]),
                technical_seo=seo_imp.get("technical_seo", ["Implement schema.org JSON-LD structured data"]),
            ),
            llm_metadata=LLMMetadata(
                provider="openai",
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_usd=estimated_cost,
            ),
        )
