"""
Voyant API - FastAPI Application

Production REST API for Voyant v3.0.0.
All endpoints follow SRS ISO Part 5 OpenAPI specification.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from voyant.api.routes import sources, jobs, sql, governance, presets, artifacts, health, discovery, search
from voyant.api.middleware import (
    TenantMiddleware, 
    RequestIdMiddleware, 
    APIVersionMiddleware,
    get_version_info,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Voyant API starting up...")
    yield
    logger.info("Voyant API shutting down...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Voyant API",
        description="Autonomous Data Intelligence for AI Agents",
        version="3.0.0",
        lifespan=lifespan,
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom middleware (order matters - last added runs first)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(APIVersionMiddleware)
    
    # Register routes
    app.include_router(health.router, tags=["health"])
    app.include_router(sources.router, prefix="/v1", tags=["sources"])
    app.include_router(jobs.router, prefix="/v1", tags=["jobs"])
    app.include_router(sql.router, prefix="/v1", tags=["sql"])
    app.include_router(governance.router, prefix="/v1", tags=["governance"])
    app.include_router(presets.router, prefix="/v1", tags=["presets"])
    app.include_router(presets.router, prefix="/v1", tags=["presets"])
    app.include_router(artifacts.router, prefix="/v1", tags=["artifacts"])
    app.include_router(discovery.router, prefix="/v1", tags=["discovery"])
    app.include_router(search.router, prefix="/v1", tags=["search"])
    
    # Version info endpoint
    @app.get("/version", tags=["meta"])
    async def version():
        """Get API version information and negotiation details."""
        return get_version_info()
    
    return app


app = create_app()

