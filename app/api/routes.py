"""FastAPI route handlers for NEXUS Link Analysis and Social Publishing Engine."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.schemas import (
    HealthResponse,
    LinkAnalysisRequest,
    LinkAnalysisResponse,
    PlatformsResponse,
    PostingRequest,
    PostingResponse,
)
from app.services.llm.manager import llm_service
from app.services.posting_service import PostingService, posting_service
from app.services.scraper import ScrapingError, scraper_service
from app.utils.logging import logger
from app.utils.ssrf import SSRFValidationError

router = APIRouter()


def get_posting_service() -> PostingService:
    """Dependency provider for PostingService."""
    return posting_service


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    tags=["System"],
)
async def health_check(
    service: PostingService = Depends(get_posting_service),
) -> HealthResponse:
    """Verify application health and report active platform & LLM integrations."""
    platforms = service.get_platforms_info()
    configured_count = sum(1 for p in platforms if p.configured)
    default_provider = llm_service.get_provider()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        configured_platforms_count=configured_count,
        total_platforms_count=len(platforms),
        llm_configured=default_provider.is_configured(),
        active_llm_provider=default_provider.provider_name,
    )


@router.get(
    "/platforms",
    response_model=PlatformsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Supported Platforms",
    tags=["Publishing"],
)
async def list_platforms(
    service: PostingService = Depends(get_posting_service),
) -> PlatformsResponse:
    """Return status, description, and documentation for all supported publishing adapters."""
    platforms = service.get_platforms_info()
    configured_count = sum(1 for p in platforms if p.configured)

    return PlatformsResponse(
        total_platforms=len(platforms),
        configured_platforms=configured_count,
        platforms=platforms,
    )


@router.post(
    "/posting",
    response_model=PostingResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish Content to Multi-Platform Engine",
    tags=["Publishing"],
)
async def publish_content(
    payload: PostingRequest,
    service: PostingService = Depends(get_posting_service),
) -> PostingResponse:
    """Publish a validated message across all configured platforms concurrently."""
    return await service.publish_message(payload.message)


@router.post(
    "/link-analysis",
    response_model=LinkAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-Powered Website Link Analysis",
    tags=["Link Analysis"],
)
async def analyze_link(
    payload: LinkAnalysisRequest,
) -> LinkAnalysisResponse:
    """Scrape and analyze a target website URL using Google Gemini / LLM.

    Capabilities:
    1. SSRF & redirect validation (blocking internal, cloud metadata, and loopback IPs).
    2. HTML structure & metadata extraction via HTTPX and BeautifulSoup.
    3. Structured Pydantic extraction containing:
       - Top 5 services offered.
       - Target audience identification.
       - Competitor analysis (direct, indirect, differentiators).
       - 5 target search queries tailored for Google, Facebook, Instagram, LinkedIn, and X.
       - SEO improvements (title, metadata, content, technical).
       - LLM execution telemetry & pricing estimation.
    """
    logger.info("Received Link Analysis request for URL: %s", payload.url)

    # 1. Scrape website with SSRF protection
    try:
        scraped_data = await scraper_service.fetch_and_extract(payload.url)
    except SSRFValidationError as exc:
        logger.warning("SSRF check blocked request to %s: %s", payload.url, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation (SSRF Protection): {exc}",
        ) from exc
    except ScrapingError as exc:
        logger.error("Failed to scrape %s: %s", payload.url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch content from target website: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during scraping: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error scraping website: {exc}",
        ) from exc

    # 2. Select configured LLM Provider
    provider = llm_service.get_provider(payload.provider)
    if not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"LLM provider '{provider.provider_name}' is not configured. "
                "Please set GEMINI_API_KEY in your .env file or environment variables."
            ),
        )

    # 3. Analyze content with LLM
    try:
        analysis_result = await provider.analyze_website_content(payload.url, scraped_data)
        return analysis_result
    except PermissionError as exc:
        logger.error("LLM authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"LLM Provider Authentication Failed: {exc}",
        ) from exc
    except (TimeoutError, ConnectionError) as exc:
        logger.error("LLM network or timeout error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"LLM Provider Communication Timeout: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("LLM analysis failed for %s: %s", payload.url, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM Analysis Failed: {exc}",
        ) from exc
