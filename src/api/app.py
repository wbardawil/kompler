"""Kompler FastAPI application factory."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events."""
    # Startup
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Initialize Sentry
    yield
    # Shutdown
    # TODO: Close connections


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Kompler",
        description="AI document intelligence — make your business documents work for you",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow any origin in dev/production (API key auth handles security)
    origins = settings.cors_origins_list
    if settings.environment == "production" or "*" in origins:
        origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from src.api.routes.health import router as health_router
    from src.api.routes.documents import router as documents_router
    from src.api.routes.chat import router as chat_router
    from src.api.routes.usage import router as usage_router
    from src.api.routes.alerts import router as alerts_router
    from src.api.routes.graph import router as graph_router
    from src.api.routes.compliance import router as compliance_router
    from src.api.routes.onboarding import router as onboarding_router
    from src.api.routes.dashboard import router as dashboard_router
    from src.api.routes.upload_guide import router as upload_guide_router
    from src.api.routes.compliance_map import router as compliance_map_router

    app.include_router(health_router, tags=["health"])
    app.include_router(documents_router, prefix="/api/v1", tags=["documents"])
    app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
    app.include_router(usage_router, prefix="/api/v1", tags=["usage"])
    app.include_router(alerts_router, prefix="/api/v1", tags=["alerts"])
    app.include_router(graph_router, prefix="/api/v1", tags=["graph"])
    app.include_router(compliance_router, prefix="/api/v1", tags=["compliance"])
    app.include_router(onboarding_router, prefix="/api/v1", tags=["onboarding"])
    app.include_router(dashboard_router, prefix="/api/v1", tags=["dashboard"])
    app.include_router(upload_guide_router, prefix="/api/v1", tags=["upload"])
    app.include_router(compliance_map_router, prefix="/api/v1", tags=["compliance-map"])

    return app


app = create_app()
