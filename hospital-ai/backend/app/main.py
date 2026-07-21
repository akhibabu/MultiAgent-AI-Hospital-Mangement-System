"""Application entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.supabase_jwt import SupabaseJWTMiddleware

settings = get_settings()
logger = get_logger("hospital_ai")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)
    logger.info(
        "Starting %s v%s [%s]",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory used by Uvicorn and tests."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Multi-Agent AI Hospital Management System API. "
            "Authentication via Supabase Auth (JWT)."
        ),
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SupabaseJWTMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(api_router)

    @app.get("/", tags=["root"])
    async def root() -> dict:
        return {
            "message": f"Welcome to {settings.app_name}",
            "docs": "/docs",
            "health": "/health",
            "version": settings.app_version,
        }

    return app


app = create_app()
