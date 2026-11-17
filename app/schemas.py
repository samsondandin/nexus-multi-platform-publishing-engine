"""Pydantic request and response schemas for NEXUS."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.validation import validate_message_content


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
