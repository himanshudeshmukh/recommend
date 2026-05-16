from __future__ import annotations
 
"""Application configuration helpers.
 
 This module keeps configuration logic centralized so the rest of the code can
 Stay focused on business behavior instead of environment parsing.
"""
 
 # Import the standard library dataclass helper so we can keep configuration
 # immutable and explicit.
from dataclasses import dataclass
 
 # Import the LRU cache decorator so we build settings only once per process.
from functools import lru_cache
 
 # Import operating-system helpers so we can read environment variables.
import os
 
 # Import pathlib for safe cross-platform path handling.
from pathlib import Path
 
import logging
 
logger = logging.getLogger(__name__)
 
 
 # Define a tiny helper that converts common string values into booleans.
def _read_bool_env(variable_name: str, default_value: bool) -> bool:
     """Read a boolean value from the environment.
 
     Args:
         Variable_name: The environment variable name to read.
         Default_value: The fallback value to use when the variable is missing.
 
     Returns:
         A normalized boolean value.
     """
 
     # Read the raw environment variable value.
     raw_value = os.getenv(variable_name)
 
     # Return the caller’s default when the variable is absent.
     if raw_value is None:
         return default_value
 
     # Normalize the string and compare it against common truthy tokens.
     return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}
 
 
 # Define the immutable settings object used by the application.
@dataclass(frozen=True)
class Settings:
     """Strongly typed application settings."""
 
     # Store the FastAPI application name.
     app_name: str
 
     # Store the service version string.
     app_version: str
 
     # Store the API prefix used by the router.
     api_prefix: str
 
     # Store the Hugging Face model name used for Fashionpedia detection.
     fashionpedia_model_name: str
 
     # Store the preferred device value such as `cpu`, `cuda`, or `auto`.
     model_device: str
 
     # Store the minimum confidence threshold used for detector outputs.
     detection_threshold: float
 
     # Store the maximum allowed upload size in bytes.
     max_upload_size_bytes: int
 
     # Store the number of dominant colors to extract from an image.
     dominant_color_count: int
 
     # Store how many outfit recommendations to return.
     recommendation_count: int
 
     # Store whether the model should be warmed during startup.
     warm_model_on_startup: bool
 
     # Store the absolute path to the local Fashionpedia category catalog.
     category_catalog_path: Path
 
 
 # Cache the settings object so every request reuses the same configuration.
@lru_cache(maxsize=1)
def get_settings() -> Settings:
     """Build and cache the application settings."""
 
     logger.info("⚙️  Building application settings from environment variables (with sensible defaults)...")
 
     # Resolve the `app` directory regardless of the current working directory.
     app_directory = Path(__file__).resolve().parents[1]
 
     # Point to the checked-in Fashionpedia category and attribute description file.
     catalog_path = app_directory / "data" / "category_attributes_descriptions.json"
 
     settings = Settings(
         app_name=os.getenv("APP_NAME", "Fashionpedia Outfit APIs"),
         app_version=os.getenv("APP_VERSION", "1.0.0"),
         api_prefix=os.getenv("API_PREFIX", "/api/v1"),
         fashionpedia_model_name=os.getenv(
             "FASHIONPEDIA_MODEL_NAME",
             "valentinafevu/yolos-fashionpedia",
         ),
         model_device=os.getenv("MODEL_DEVICE", "auto"),
         detection_threshold=float(os.getenv("DETECTION_THRESHOLD", "0.35")),
         max_upload_size_bytes=int(os.getenv("MAX_UPLOAD_SIZE_BYTES", "15728640")),
         dominant_color_count=int(os.getenv("DOMINANT_COLOR_COUNT", "5")),
         recommendation_count=int(os.getenv("RECOMMENDATION_COUNT", "3")),
         warm_model_on_startup=_read_bool_env("WARM_MODEL_ON_STARTUP", False),
         category_catalog_path=catalog_path,
     )
 
     logger.info("⚙️  Settings built successfully:")
     logger.info("   App name: '%s', Version: '%s'", settings.app_name, settings.app_version)
     logger.info("   API prefix: '%s'", settings.api_prefix)
     logger.info("   Model: '%s' on device '%s'", settings.fashionpedia_model_name, settings.model_device)
     logger.info("   Detection threshold: %.2f (items below %.0f%% confidence are ignored)",
                 settings.detection_threshold, settings.detection_threshold * 100)
     logger.info("   Max upload size: %d bytes (%.1f MB)", settings.max_upload_size_bytes,
                 settings.max_upload_size_bytes / (1024 * 1024))
     logger.info("   Dominant color count: %d, Recommendation count: %d",
                 settings.dominant_color_count, settings.recommendation_count)
     logger.info("   Warm model on startup: %s", settings.warm_model_on_startup)
     logger.info("   Catalog path: %s", settings.category_catalog_path)
 
     return settings


 