"""FastAPI application entry point for NEXUS Multi-Platform Publishing Engine."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.routes import router
from app.config import settings
from app.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup and shutdown event handling."""
    logger.info("Initializing NEXUS Multi-Platform Publishing Engine...")
    logger.info("Environment: %s | Host: %s | Port: %d", settings.ENVIRONMENT, settings.HOST, settings.PORT)
    yield
    logger.info("Shutting down NEXUS Engine. Cleaning up resources.")


app = FastAPI(
    title="NEXUS — Multi-Platform Publishing Engine",
    description=(
        "A modular asynchronous Python publishing engine built with FastAPI, "
        "integrating multiple third-party platforms through their official APIs "
        "with independent execution, validation, and fault-tolerant publishing."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Centralized handler for request validation failures, returning structured 422 errors."""
    error_messages = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        error_messages.append(f"{loc}: {msg}" if loc else msg)

    formatted_error = "; ".join(error_messages)
    logger.warning("Request validation failed on %s: %s", request.url.path, formatted_error)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": formatted_error,
            "errors": exc.errors(),
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
        "name": "Multi-Platform Publishing Engine",
        "version": "1.0.0",
        "description": "Modular asynchronous publishing engine for social networks and messaging platforms.",
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "posting_endpoint": "POST /posting",
    }


# Include core routing
app.include_router(router)
