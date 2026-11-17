"""FastAPI route handlers for NEXUS."""

from fastapi import APIRouter, Depends, status
from app.config import settings
from app.schemas import (
    HealthResponse,
    PlatformsResponse,
    PostingRequest,
    PostingResponse,
)
from app.services.posting_service import PostingService, posting_service

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
    """Verify application health and reporting count of configured platforms."""
    platforms = service.get_platforms_info()
    configured_count = sum(1 for p in platforms if p.configured)

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        configured_platforms_count=configured_count,
        total_platforms_count=len(platforms),
    )


@router.get(
    "/platforms",
    response_model=PlatformsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Supported Platforms",
    tags=["Platforms"],
)
async def list_platforms(
    service: PostingService = Depends(get_posting_service),
) -> PlatformsResponse:
    """Return status, description, and documentation for all supported platform integrations."""
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
    """Publish a validated message across all configured platforms concurrently.

    Requirements:
    - Message length <= 200 characters.
    - Exactly one valid HTTP/HTTPS URL.
    - Completely independent execution per platform.
    - Fault-isolated results with verified post URLs and timestamps.
    """
    return await service.publish_message(payload.message)
