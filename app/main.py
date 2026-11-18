"""FastAPI application entry point for NEXUS Multi-Platform Publishing & Link Analysis Engine."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings
from app.services.llm.manager import llm_service
from app.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup and shutdown event handling."""
    logger.info("Initializing NEXUS Engine...")
    logger.info("Environment: %s | Host: %s | Port: %d", settings.ENVIRONMENT, settings.HOST, settings.PORT)
    active_llm = llm_service.get_provider()
    logger.info("Default LLM Provider: %s (Configured: %s)", active_llm.provider_name, active_llm.is_configured())
    yield
    logger.info("Shutting down NEXUS Engine. Cleaning up resources.")


app = FastAPI(
    title="NEXUS — AI-Powered Website Link Analysis & Multi-Platform Engine",
    description=(
        "A modular asynchronous Python engine built with FastAPI. Features:\n"
        "1. AI-Powered Website Link Analysis (`POST /link-analysis`) with SSRF protection, "
        "HTML extraction, structured Pydantic output, top 5 services, target audience, "
        "competitor analysis, search queries for 5 platforms (Google, FB, IG, LinkedIn, X), "
        "actionable SEO improvements, and LLM cost estimation.\n"
        "2. Fault-isolated multi-platform social publisher (`POST /posting`) supporting Bluesky, "
        "Mastodon, Telegram, Discord, and Reddit."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Centralized handler for request validation failures, returning structured 422 errors."""
    error_details = []
    messages = []
    for err in exc.errors():
        loc = " -> ".join(str(part) for part in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        error_type = err.get("type", "value_error")
        messages.append(f"{loc}: {msg}" if loc else msg)
        error_details.append({
            "loc": err.get("loc", []),
            "msg": msg,
            "type": error_type,
        })

    formatted_error = "; ".join(messages)
    logger.warning("Request validation failed on %s: %s", request.url.path, formatted_error)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": formatted_error,
            "errors": error_details,
        },
    )


@app.get(
    "/",
    tags=["System"],
    summary="Root Project Information",
)
async def root() -> dict[str, str]:
    """Project metadata and direct links to API documentation."""
    return {
        "project": "NEXUS",
        "name": "AI-Powered Website Link Analysis & Publishing Engine",
        "version": "2.0.0",
        "description": "FastAPI engine for website link analysis & multi-platform social broadcasting.",
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "link_analysis_endpoint": "POST /link-analysis",
        "posting_endpoint": "POST /posting",
    }


# Include core routing
app.include_router(router)
