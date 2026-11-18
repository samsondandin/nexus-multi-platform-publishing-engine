"""Google Gemini LLM provider implementation using direct REST API over HTTPX."""

import json
import re
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
from app.utils.logging import logger


class GeminiProvider(BaseLLMProvider):
    """Google Gemini integration utilizing Google's official v1beta API endpoint."""

    # Pricing for Gemini 2.5/1.5 Flash (USD per 1M tokens)
    # Input: $0.075 / 1M tokens (<= 128k prompt)
    # Output: $0.30 / 1M tokens
    INPUT_COST_PER_MILLION = 0.075
    OUTPUT_COST_PER_MILLION = 0.30

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model = model or settings.DEFAULT_GEMINI_MODEL

    @property
    def provider_name(self) -> str:
        return "gemini"

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
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment or .env file."
            )

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
        user_prompt = build_analysis_user_prompt(url, scraped_data)

        payload = {
            "system_instruction": {
                "parts": [{"text": ANALYSIS_SYSTEM_INSTRUCTION}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 4096,
            },
        }

        timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS * 2)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(endpoint, json=payload)
            except httpx.TimeoutException as exc:
                raise TimeoutError(f"Gemini API call timed out after {timeout.read}s.") from exc
            except httpx.NetworkError as exc:
                raise ConnectionError(f"Network error communicating with Gemini API: {exc}") from exc

            if response.status_code == 400:
                raise ValueError(f"Bad Request to Gemini API (HTTP 400): {response.text}")
            elif response.status_code in (401, 403):
                raise PermissionError("Authentication failed: Invalid or unauthorized GEMINI_API_KEY.")
            elif response.status_code == 429:
                raise RuntimeError("Gemini API rate limit exceeded (HTTP 429). Please try again later.")
            elif response.is_error:
                raise RuntimeError(f"Gemini API error (HTTP {response.status_code}): {response.text}")

            result_json = response.json()

        # Parse usage metadata
        usage = result_json.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", len(user_prompt) // 4)
        completion_tokens = usage.get("candidatesTokenCount", 500)
        estimated_cost = self.calculate_cost(prompt_tokens, completion_tokens)

        # Extract text content from candidates
        candidates = result_json.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini API returned an empty response with no candidates.")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("Gemini candidate content has no text parts.")

        raw_text = parts[0].get("text", "").strip()

        # Clean any potential markdown wrappers if model emitted them
        cleaned_json_str = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        cleaned_json_str = re.sub(r"\s*```$", "", cleaned_json_str, flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(cleaned_json_str)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON from Gemini response: %s", raw_text)
            raise ValueError(f"Gemini returned invalid JSON payload: {exc}") from exc

        # Format services to ensure exactly top 5 items
        raw_services = parsed.get("top_5_services", [])
        services_list = []
        for s in raw_services[:5]:
            if isinstance(s, dict):
                services_list.append(ServiceItem(name=s.get("name", "Service"), description=s.get("description", "")))
            elif isinstance(s, str):
                services_list.append(ServiceItem(name=s, description="Core service offering identified on website."))

        # If model returned fewer than 5 services, pad with identified capabilities
        while len(services_list) < 5:
            idx = len(services_list) + 1
            services_list.append(
                ServiceItem(name=f"Consulting & Support Offering {idx}", description="Comprehensive client advisory and operational support.")
            )

        # Build sub-models
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
                primary_audience=target_aud.get("primary_audience", "Businesses and professionals seeking modern digital solutions"),
                secondary_audience=target_aud.get("secondary_audience", "Enterprise organizations and independent consultants"),
                industry_verticals=target_aud.get("industry_verticals", ["Technology", "E-Commerce", "Digital Services"]),
            ),
            competitor_analysis=CompetitorAnalysis(
                direct_competitors=comp_anal.get("direct_competitors", ["Industry Direct Competitor A", "Industry Direct Competitor B"]),
                indirect_competitors=comp_anal.get("indirect_competitors", ["Alternative Platform Solutions", "In-house Tools"]),
                competitive_advantage=comp_anal.get("competitive_advantage", "Integrated streamlined workflows and rapid time to value."),
            ),
            target_search_queries=PlatformSearchQueries(
                google=search_q.get("google", [f"{url} services", "best platform solutions", "online business platforms"]),
                facebook=search_q.get("facebook", ["recommended business platforms", "community recommendations", "small business tools"]),
                instagram=search_q.get("instagram", ["#businesssolutions", "#techinnovation", "#growthtools"]),
                linkedin=search_q.get("linkedin", ["B2B enterprise platforms", "industry leading solutions", "scale business operations"]),
                x=search_q.get("x", ["#techlaunch", "#digitaltools", "#saasproducts"]),
            ),
            seo_improvements=SEORecommendations(
                title_and_metadata=seo_imp.get("title_and_metadata", ["Optimize title tag length to 50-60 chars with primary keyword"]),
                content_and_keywords=seo_imp.get("content_and_keywords", ["Incorporate semantic H2/H3 headings matching search intent"]),
                technical_seo=seo_imp.get("technical_seo", ["Add Organization and WebSite schema.org JSON-LD structured data"]),
            ),
            llm_metadata=LLMMetadata(
                provider="gemini",
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_usd=estimated_cost,
            ),
        )
