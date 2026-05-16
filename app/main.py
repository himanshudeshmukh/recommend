from __future__ import annotations

"""FastAPI application entry point."""

# Import logging so startup events can be recorded.
import logging

# Import the FastAPI framework.
from fastapi import FastAPI

# Import API routes and shared configuration helpers.
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.dependencies import get_detector


# Configure application logging before creating the app object.
configure_logging()

logger = logging.getLogger(__name__)

logger.info("═══════════════════════════════════════════════════════════════")
logger.info("🚀 Fashionpedia FastAPI Application — Starting up...")
logger.info("═══════════════════════════════════════════════════════════════")

# Read the shared immutable settings object.
settings = get_settings()

logger.info(
    "⚙️  Settings loaded — app: '%s' v%s, API prefix: '%s'.",
    settings.app_name,
    settings.app_version,
    settings.api_prefix,
)

logger.info(
    "⚙️  Model: '%s', device: '%s', detection threshold: %.2f.",
    settings.fashionpedia_model_name,
    settings.model_device,
    settings.detection_threshold,
)

logger.info(
    "⚙️  Max upload size: %.1f MB, dominant colors: %d, recommendations: %d.",
    settings.max_upload_size_bytes / (1024 * 1024),
    settings.dominant_color_count,
    settings.recommendation_count,
)

# Create the FastAPI application with friendly metadata.
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

logger.info(
    "✅ FastAPI application object created. Docs at /docs, ReDoc at /redoc."
)

# Register the versioned API router with the application.
app.include_router(router, prefix=settings.api_prefix)

logger.info(
    "✅ API routes registered under prefix '%s'.",
    settings.api_prefix,
)


# Warm the detector on startup when the configuration requests it.
@app.on_event("startup")
async def startup_event() -> None:
    """Optionally warm the detector so the first request is faster."""

    logger.info("═══════════════════════════════════════════════════════════════")
    logger.info("🏁 Application startup event triggered.")
    logger.info("═══════════════════════════════════════════════════════════════")

    if settings.warm_model_on_startup:
        logger.info(
            "🔥 WARM_MODEL_ON_STARTUP is enabled — pre-loading the AI model now..."
        )

        try:
            get_detector().warmup()

            logger.info(
                "✅ Fashionpedia detector warmed successfully during startup — the first request will be fast."
            )

        except Exception:
            logger.exception(
                "❌ Failed to warm the Fashionpedia detector during startup. "
                "The model will attempt to load on the first request instead."
            )

    else:
        logger.info(
            "ℹ️  WARM_MODEL_ON_STARTUP is disabled — the AI model will load lazily on the first request."
        )

    logger.info("═══════════════════════════════════════════════════════════════")
    logger.info("🟢 Application is ready to accept requests!")
    logger.info("═══════════════════════════════════════════════════════════════")