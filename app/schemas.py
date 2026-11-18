"""Pydantic request and response schemas for NEXUS Link Analysis and Posting."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.validation import validate_message_content

# ==============================================================================
# 1. Multi-Platform Publishing Schemas (POST /posting)
# ==============================================================================

class OverallStatus(str, Enum):
    """Overall status across all attempted publishing platforms."""

    ALL_SUCCESS = "all_success"
    PARTIAL_SUCCESS = "partial_success"
    ALL_FAILED = "all_failed"
    NO_PLATFORMS_CONFIGURED = "no_platforms_configured"


class PlatformPublishStatus(str, Enum):
    """Publishing status for an individual platform."""

    SUCCESS = "success"
    FAILED = "failed"
    UNCONFIGURED = "unconfigured"


class PostingRequest(BaseModel):
    """Payload for POST /posting endpoint."""

    message: str = Field(
        ...,
        description="The content to publish. Must be 1-200 characters and contain exactly one valid HTTP/HTTPS URL.",
        examples=["Check out our latest business platform and grow your online visibility. https://example.com"],
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        return validate_message_content(v)


class PlatformResult(BaseModel):
    """Execution result for a single target platform."""

    platform: str = Field(..., description="Name of the third-party publishing platform")
    status: PlatformPublishStatus = Field(..., description="Outcome of the publishing attempt")
    posted_url: Optional[str] = Field(
        None,
        description="Public URL of the published post verified from official platform API response, or null",
    )
    public_access: Optional[bool] = Field(
        None,
        description="Whether the published post is publicly accessible, or null if unverified/failed",
    )
    date: Optional[str] = Field(
        None,
        description="UTC date of the publishing event in YYYY-MM-DD format, or null",
    )
    time: Optional[str] = Field(
        None,
        description="UTC time of the publishing event in HH:MM:SS format, or null",
    )
    error: Optional[str] = Field(
        None,
        description="Human-readable error details if publishing failed, or null on success",
    )


class PostingResponse(BaseModel):
    """API response contract for POST /posting."""

    success: bool = Field(
        ...,
        description="True only if all configured platform publishing attempts succeeded without failure",
    )
    overall_status: OverallStatus = Field(
        ...,
        description="Summary status across all evaluated platforms",
    )
    results: List[PlatformResult] = Field(
        ...,
        description="Individual execution results for each evaluated platform",
    )


class HealthResponse(BaseModel):
    """Response schema for GET /health."""

    status: str
    version: str
    environment: str
    configured_platforms_count: int
    total_platforms_count: int
    llm_configured: bool
    active_llm_provider: str


class PlatformInfo(BaseModel):
    """Metadata describing a supported platform."""

    platform: str
    configured: bool
    public_access_supported: bool
    description: str
    docs_url: str


class PlatformsResponse(BaseModel):
    """Response schema for GET /platforms."""

    total_platforms: int
    configured_platforms: int
    platforms: List[PlatformInfo]


# ==============================================================================
# 2. AI-Powered Website Link Analysis Schemas (POST /link-analysis)
# ==============================================================================

class LinkAnalysisRequest(BaseModel):
    """Payload for POST /link-analysis endpoint."""

    url: str = Field(
        ...,
        description="The website URL to scrape and analyze. Must be a valid public HTTP or HTTPS web address.",
        examples=["https://stripe.com"],
    )
    provider: Optional[str] = Field(
        None,
        description="Optional LLM provider to override default ('gemini', 'openai', or 'groq')",
    )

    @field_validator("url")
    @classmethod
    def validate_website_url(cls, v: str) -> str:
        trimmed = v.strip() if v else ""
        if not trimmed:
            raise ValueError("URL cannot be empty.")
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("Website URL must start with http:// or https://")
        return trimmed


class ServiceItem(BaseModel):
    """Service or core offering discovered on the website."""

    name: str = Field(..., description="Service or product title")
    description: str = Field(..., description="Description of the service and value proposition")


class TargetAudience(BaseModel):
    """Target customer audience breakdown."""

    primary_audience: str = Field(..., description="Primary ideal customer profile (ICP)")
    secondary_audience: str = Field(..., description="Secondary customer segment or market")
    industry_verticals: List[str] = Field(default_factory=list, description="Target industry verticals or sectors")


class CompetitorAnalysis(BaseModel):
    """Competitive landscape and positioning."""

    direct_competitors: List[str] = Field(default_factory=list, description="Direct competitors offering similar services")
    indirect_competitors: List[str] = Field(default_factory=list, description="Indirect or substitute competitors")
    competitive_advantage: str = Field(..., description="Key differentiators and unique selling points")


class PlatformSearchQueries(BaseModel):
    """5 targeted search queries tailored across Google, Facebook, Instagram, LinkedIn, and X."""

    google: List[str] = Field(..., description="High-intent search queries for Google Search / SEO")
    facebook: List[str] = Field(..., description="Community and interest-based queries for Facebook")
    instagram: List[str] = Field(..., description="Hashtags and discovery keywords for Instagram")
    linkedin: List[str] = Field(..., description="B2B, hiring, and professional solution queries for LinkedIn")
    x: List[str] = Field(..., description="Hashtags, trending topics, and conversational queries for X (Twitter)")


class SEORecommendations(BaseModel):
    """Actionable search engine optimization recommendations."""

    title_and_metadata: List[str] = Field(default_factory=list, description="Title tag and meta description suggestions")
    content_and_keywords: List[str] = Field(default_factory=list, description="Content depth, semantic keywords, and heading improvements")
    technical_seo: List[str] = Field(default_factory=list, description="Technical SEO, schema markup, and performance insights")


class LLMMetadata(BaseModel):
    """Telemetry describing LLM execution and cost estimation."""

    provider: str = Field(..., description="LLM provider invoked (e.g. Google Gemini, OpenAI)")
    model: str = Field(..., description="Model identifier used (e.g. gemini-2.5-flash)")
    prompt_tokens: int = Field(default=0, description="Estimated input/prompt token count")
    completion_tokens: int = Field(default=0, description="Estimated output/completion token count")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated query cost in USD based on provider pricing")


class LinkAnalysisResponse(BaseModel):
    """Structured response contract for POST /link-analysis."""

    url: str = Field(..., description="Analyzed website URL")
    scraped_title: Optional[str] = Field(None, description="Page title extracted from HTML")
    scraped_description: Optional[str] = Field(None, description="Meta description extracted from HTML")
    top_5_services: List[ServiceItem] = Field(..., description="Exactly top five services or products identified")
    target_audience: TargetAudience = Field(..., description="Target audience identification")
    competitor_analysis: CompetitorAnalysis = Field(..., description="Competitor and market positioning analysis")
    target_search_queries: PlatformSearchQueries = Field(
        ...,
        description="Target search queries across Google, Facebook, Instagram, LinkedIn, and X",
    )
    seo_improvements: SEORecommendations = Field(..., description="Actionable SEO improvement recommendations")
    llm_metadata: LLMMetadata = Field(..., description="Execution telemetry and cost estimation")
