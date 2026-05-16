from __future__ import annotations

"""
Singleton-style dependency factories for the FastAPI service.
"""

from functools import lru_cache
import logging

from app.core.config import get_settings
from app.services.fashionpedia_catalog import FashionpediaCatalog
from app.services.fashionpedia_detector import FashionpediaDetector
from app.services.image_analysis_service import ImageAnalysisService
from app.services.outfit_recommender import OutfitRecommender


logger = logging.getLogger(__name__)


# ============================================================================
# FASHIONPEDIA CATALOG
# ============================================================================

@lru_cache(maxsize=1)
def get_catalog() -> FashionpediaCatalog:
    """
    Return the singleton Fashionpedia catalog.
    """

    logger.info(
        "📦 Creating the Fashionpedia catalog singleton "
        "(loading fashion categories and attributes from disk)..."
    )

    settings = get_settings()

    catalog = FashionpediaCatalog(
        settings.category_catalog_path,
    )

    logger.info(
        "📦 Fashionpedia catalog singleton created — "
        "%d categories, %d attributes available.",
        catalog.category_count,
        catalog.attribute_count,
    )

    return catalog


# ============================================================================
# FASHIONPEDIA DETECTOR
# ============================================================================

@lru_cache(maxsize=1)
def get_detector() -> FashionpediaDetector:
    """
    Return the singleton Fashionpedia detector.
    """

    logger.info(
        "📦 Creating the Fashionpedia detector singleton "
        "(the AI model that finds clothing in images)..."
    )

    detector = FashionpediaDetector(
        get_settings(),
        get_catalog(),
    )

    logger.info(
        "📦 Fashionpedia detector singleton created — "
        "model will be loaded on first use."
    )

    return detector


# ============================================================================
# IMAGE ANALYSIS SERVICE
# ============================================================================

@lru_cache(maxsize=1)
def get_image_analysis_service() -> ImageAnalysisService:
    """
    Return the singleton image-analysis service.
    """

    logger.info(
        "📦 Creating the ImageAnalysisService singleton "
        "(orchestrates the full image analysis pipeline)..."
    )

    service = ImageAnalysisService(
        get_settings(),
        get_detector(),
    )

    logger.info(
        "📦 ImageAnalysisService singleton created and ready."
    )

    return service


# ============================================================================
# OUTFIT RECOMMENDER
# ============================================================================

@lru_cache(maxsize=1)
def get_outfit_recommender() -> OutfitRecommender:
    """
    Return the singleton outfit recommender.
    """

    logger.info(
        "📦 Creating the OutfitRecommender singleton "
        "(generates outfit suggestions based on context)..."
    )

    recommender = OutfitRecommender(
        get_settings(),
        get_catalog(),
        get_detector(),
    )

    logger.info(
        "📦 OutfitRecommender singleton created and ready."
    )

    return recommender