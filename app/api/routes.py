from __future__ import annotations
 
"""HTTP routes for the Fashionpedia API service.
 
 ╔══════════════════════════════════════════════════════════════════════════════╗
 ║                         API ROUTES — HIGH-LEVEL OVERVIEW                     ║
 ║                                                                              ║
 ║  This module defines all the HTTP endpoints (URLs) that the service          ║
 ║  exposes. Think of this as the "front door" — it receives requests from      ║
 ║  clients, validates them, and routes them to the right internal service.     ║
 ║                                                                              ║
 ║  ═══════════════════════════════════════════════════════════════════════════ ║
 ║  ENDPOINTS SUMMARY:                                                          ║
 ║  ═══════════════════════════════════════════════════════════════════════════ ║
 ║                                                                              ║
 ║  GET  /api/v1/health              — Lightweight liveness probe               ║
 ║  POST /api/v1/images/analyze      — Upload a fashion image → get analysis    ║
 ║  POST /api/v1/outfits/recommend   — Get outfit suggestions for an occasion   ║
 ║                                                                              ║
 ║  ═══════════════════════════════════════════════════════════════════════════ ║
 ║  HTTP STATUS CODES USED ACROSS ALL ENDPOINTS:                                ║
 ║  ═══════════════════════════════════════════════════════════════════════════ ║
 ║                                                                              ║
 ║  200 OK              — Request succeeded. Response body contains the data.   ║
 ║  400 Bad Request      — Client sent invalid data. For example:               ║
 ║                         • Uploaded file is not an image (wrong MIME type)    ║
 ║                         • Uploaded image file is empty (0 bytes)             ║
 ║                         • Image bytes are corrupted and cannot be decoded    ║
 ║                         • Required form field "occasion" is missing          ║
 ║                         • Form field has an invalid data type                ║
 ║  413 Payload Too Large — Uploaded image exceeds the max file size limit      ║
 ║                          (default: 15 MB, configurable via env var).         ║
 ║  422 Unprocessable     — FastAPI's automatic validation failed. This means   ║
 ║      Entity             a required field was missing or had the wrong type.  ║
 ║                          FastAPI returns this automatically; we do NOT need  ║
 ║                          to raise it manually.                               ║
 ║  500 Internal Server   — An unexpected bug or crash happened inside the      ║
 ║      Error               server. The client gets a generic error message     ║
 ║                          so internal details are not leaked.                 ║
 ║  503 Service           — The AI model could not be loaded or is temporarily  ║
 ║      Unavailable         unavailable. The client should retry later.         ║
 ║                                                                              ║
 ║  ═════���═════════════════════════════════════════════════════════════════════  ║
 ║  FLOW FOR POST /images/analyze (HIGH LEVEL):                                 ║
 ║  ════════════════════════════════════════════════════════════════════���══════  ║
 ║                                                                              ║
 ║  1. Client uploads an image file + optional text context fields              ║
 ║  2. Server validates the upload (MIME type, file size, emptiness)             ║
 ║  3. Server normalizes all text fields (lowercase, trim whitespace)           ║
 ║  4. Server hands off to the ImageAnalysisService                             ║
 ║  5. Service returns structured metadata + AI detections + style prediction   ║
 ║  6. Server returns the full JSON response to the client                      ║
 ║                                                                              ║
 ║  FLOW FOR POST /images/analyze (LOW LEVEL — inside the service):             ║
 ║  ───────────────────────────────────────────────────────────────              ║
 ║                                                                              ║
 ║  Step 1: Decode raw bytes → Pillow Image (validates the file is a real       ║
 ║          image; raises ValueError if corrupted or not an image)              ║
 ║  Step 2: Build file metadata — record file name, size in bytes, and          ║
 ║          compute SHA-256 hash for deduplication / audit trail                 ║
 ║  Step 3: Extract technical metadata — image width, height, aspect ratio,     ║
 ║          orientation (portrait/landscape/square), megapixels, color mode,    ║
 ║          alpha channel, animation frames, ICC profile, DPI, EXIF summary     ║
 ║  Step 4: Analyze image quality — compute brightness (mean grayscale),        ║
 ║          contrast (std dev), entropy (visual complexity), sharpness          ║
 ║          (Laplacian variance), edge density (Canny), dominant colors         ║
 ║          (median-cut quantization), and generate quality warnings            ║
 ║  Step 5: Run AI fashion detector — load YOLOS model (lazy, thread-safe),     ║
 ║          preprocess image, run inference on CPU/GPU, post-process outputs,   ║
 ║          filter by confidence threshold, map label IDs → Fashionpedia        ║
 ║          category names, extract crop color palettes per detection            ║
 ║  Step 6: Group detections into outfit zones — upper body, lower body,        ║
 ║          one-piece, outerwear, footwear, accessories, garment parts,         ║
 ║          closures, decorations                                               ║
 ║  Step 7: Predict context fit — score detected labels against 8 style         ║
 ║          signal sets (casual, office, formal, party, sport, travel,          ║
 ║          beach, festive), compare against user's occasion/weather to         ║
 ║          produce alignment scores and human-readable reasoning               ║
 ║                                                                              ║
 ║  ═══════════════════════════════════════════════════════════════════════════  ║
 ║  FLOW FOR POST /outfits/recommend (HIGH LEVEL):                              ║
 ║  ═══════════════════════════════════════════════════════════════════════════  ║
 ║                                                                              ║
 ║  1. Client sends occasion (required) + optional image + optional prefs       ║
 ║  2. Server validates the optional image (same checks as /images/analyze)     ║
 ║  3. Server normalizes all text fields into a clean context object            ║
 ║  4. Server hands off to the OutfitRecommender service                        ║
 ║  5. Recommender returns ranked outfit suggestions with reasoning             ║
 ║  6. Server returns the full JSON response to the client                      ║
 ║                                                                              ║
 ║  FLOW FOR POST /outfits/recommend (LOW LEVEL — inside the service):          ║
 ║  ──────────────────────────────────────────────────────────────               ║
 ║                                                                              ║
 ║  Step 1: Map occasion text → bucket (office, formal, party, festive,         ║
 ║          sport, travel, beach, casual) using keyword matching                 ║
 ║  Step 2: Map weather text + temperature → band (cold, cool, mild, warm,      ║
 ║          hot, rainy) using keyword matching + numeric ranges                  ║
 ║  Step 3: (Optional) If a reference image was uploaded, run AI detector       ║
 ║          on it to extract style cues (detected labels, dominant colors,      ║
 ║          inferred style label like "formal" or "summer casual")              ║
 ║  Step 4: Score all 11 curated templates against the context — each           ║
 ║          template gets points for matching the occasion bucket, weather       ║
 ║          band, gender hints, reference-image overlap, style preferences,     ║
 ║          and loses points for items on the user's avoid-list                  ║
 ║  Step 5: Select the top N templates (default: 3, configurable)               ║
 ║  Step 6: Personalize each template — swap out avoided items using a          ║
 ║          fallback replacement map, add weather-specific extras (umbrella     ║
 ║          for rain, scarf for cold), remove inappropriate items (coat in      ║
 ║          hot weather), apply user's color preferences or reference colors    ║
 ║  Step 7: Build final recommendations with reasoning, confidence scores,      ║
 ║          attribute-direction hints, and deprioritized item list              ║
 ╚══════════════════════════════════════════════════════════════════════════════╝
 """
 
 # ─────────────────────────────────────────────────────────────────────────────
 # IMPORTS
 # ─────────────────────────────────────────────────────────────────────────────
 
 # Import FastAPI routing primitives used to define endpoints, parse form data,
 # handle file uploads, inject dependencies, and raise HTTP errors.
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
 
 # Import FastAPI's JSONResponse so we can return structured error bodies with
 # a controlled status code and payload shape.
from fastapi.responses import JSONResponse
 
 # Import the standard logging module so we can write human-readable trace
 # messages at every step of every request for debugging and monitoring.
import logging
 
 # Import time so we can measure how long each request takes from start to
 # finish — this helps identify performance bottlenecks.
import time
 
 # Import traceback so we can capture full stack traces for unexpected errors
 # without crashing the response — the trace goes to logs, not to the client.
import traceback
 
 # Import uuid so each incoming request gets a unique 8-character tracking ID.
 # This ID appears in every log line for the request, making it easy to search
 # logs and correlate all steps of a single request.
import uuid
 
 # Import configuration helpers so we can read application settings (e.g. max
 # upload size, detection threshold) that were loaded from environment variables.
from app.core.config import get_settings
 
 # Import typed response models (Pydantic schemas) that define the exact JSON
 # shape returned by each endpoint. Also import the new ErrorResponse model
 # used for all non-2xx error payloads.
from app.models.schemas import (
     AnalyzeImageResponse,
     ErrorResponse,
     NormalizedUserContext,
     RecommendOutfitResponse,
 )
 
 # Import singleton factory functions that create and cache service instances.
 # These use @lru_cache so the heavy AI model is loaded only once per process.
from app.services.dependencies import get_image_analysis_service, get_outfit_recommender
 
 # Import the service classes so FastAPI's Depends() can type-check them.
from app.services.image_analysis_service import ImageAnalysisService
from app.services.outfit_recommender import OutfitRecommender
 
 
 # ───────────────────────────────────────────────────────────────────────────��─
 # MODULE-LEVEL SETUP
 # ─────────────────────────────────────────────────────────────────────────────
 
 # Create a module-level logger dedicated to the API routes layer.
 # All log messages from this file will be tagged with "app.api.routes" so
 # they are easy to filter in log aggregation tools (e.g. Datadog, CloudWatch).
logger = logging.getLogger(__name__)
 
 # Create the router that will be registered with the main FastAPI application.
 # The "fashionpedia" tag groups all these endpoints together in the auto-
 # generated Swagger/ReDoc documentation.
router = APIRouter(tags=["fashionpedia"])
 
 
 # ═════════════════════════════════════════════════════════════════════════════
 #                     HELPER: Build a structured error response
 # ═════════════════════════════════════════════════════════════════════════════
def _error_response(
     status_code: int,
     error: str,
     detail: str,
     request_id: str | None = None,
 ) -> JSONResponse:
     """Build a JSONResponse with the standardized ErrorResponse body.
 
     WHY THIS EXISTS:
     ────────────────
     Instead of raising HTTPException (which returns {"detail": "..."}), this
     helper returns a richer JSON body that includes the status code, a short
     machine-friendly error type, a human-readable explanation, and the request
     tracking ID. This makes it much easier for front-end developers and support
     teams to understand what went wrong.
 
     EXAMPLE OUTPUT:
     ───────────────
     {
         "status_code": 400,
         "error": "invalid_image_type",
         "detail": "Uploaded file must be an image (e.g. image/jpeg, image/png).",
         "request_id": "a1b2c3d4"
     }
 
     Args:
         status_code:  The HTTP status code to return (e.g. 400, 413, 500, 503).
         error:        A short snake_case label for programmatic error handling.
         detail:       A long human-readable explanation of what went wrong.
         request_id:   The unique request tracking ID (appears in all log lines).
 
     Returns:
         A FastAPI JSONResponse with the correct status code and body.
     """
 
     # Build the response payload using the ErrorResponse schema.
     body = ErrorResponse(
         Status_code=status_code,
         Error=error,
         Detail=detail,
         Request_id=request_id,
     )
 
     # Log the error at the appropriate severity level.
     if status_code >= 500:
         logger.error("🔴 [%s] Returning HTTP %d (%s): %s", request_id, status_code, error, detail)
     else:
         logger.warning("🟡 [%s] Returning HTTP %d (%s): %s", request_id, status_code, error, detail)
 
     # Return the JSON response with the ErrorResponse body.
     return JSONResponse(status_code=status_code, content=body.model_dump())
 
 
 # ═════════════════════════════════════════════════════════════════════════════
 #  HELPER: Normalize free-form text fields into stable lowercase strings.
 #
 #  WHY THIS EXISTS:
 #  ────────────────
 #  Users type text in many different ways. Someone might type "Office",
 #  "OFFICE", " office ", or "  Office  ". All of these should be treated
 #  as the same value: "office". This function standardizes all text input
 #  so the rest of the code can do simple string comparisons.
 #
 #  HOW IT WORKS:
 #  ─────────────
 #  1. If the value is None (not provided), return None immediately.
 #  2. Strip leading/trailing whitespace.
 #  3. Convert to lowercase.
 #  4. Collapse any multiple spaces into a single space.
 #  5. If the result is an empty string, return None (treat as "not provided").
 # ═════════════════════════════════════════════════════════════════════════════
def _normalize_text(value: str | None) -> str | None:
     """Normalize free-form input text by lowercasing, trimming, and collapsing whitespace.
 
     Args:
         value: Raw text from a form field, or None if the field was not provided.
 
     Returns:
         A cleaned lowercase string, or None if the input was empty/None.
 
     Examples:
         _normalize_text("  Office  ")  → "office"
         _normalize_text("BUSINESS casual") → "business casual"
         _normalize_text("  ")          → None
         _normalize_text(None)          → None
     """
 
     # If the user did not provide this field at all, pass through None.
     if value is None:
         return None
 
     # Strip whitespace, lowercase, and collapse multiple spaces into one.
     normalized = " ".join(value.strip().lower().split())
 
     # Log the transformation for debugging (only visible at DEBUG log level).
     logger.debug("📝 Normalized text: '%s' → '%s'.", value, normalized)
 
     # Return None instead of an empty string so downstream code can use
     # simple `if context.occasion:` checks.
     return normalized or None
 
 
 # ═════════════════════════════════════════════════════════════════════════════
 #  HELPER: Split comma-separated input into a cleaned list of unique values.
 #
 #  WHY THIS EXISTS:
 #  ────────────────
 #  Several form fields accept comma-separated lists (e.g. style_preferences,
 #  color_preferences, avoid_items). Users might type "navy, charcoal, ,NAVY"
 #  which should become ["navy", "charcoal"] — deduplicated, normalized, and
 #  with empty entries removed.
 #
 #  HOW IT WORKS:
 #  ─────────────
 #  1. If the value is None, return an empty list.
 #  2. Split the string on commas.
 #  3. Normalize each part using _normalize_text().
 #  4. Skip None results (empty parts) and duplicates.
 #  5. Return the final clean list.
 # ═════════════════════════════════════════════════════════════════════════════
def _split_csv_field(value: str | None) -> list[str]:
     """Convert a comma-separated string into a deduplicated normalized list.
 
     Args:
         value: Raw comma-separated text, or None if not provided.
 
     Returns:
         A list of unique, normalized strings. Empty if input was None.
 
     Examples:
         _split_csv_field("navy, charcoal, ,NAVY") → ["navy", "charcoal"]
         _split_csv_field("minimal")                → ["minimal"]
         _split_csv_field(None)                     → []
     """
 
     # Return an empty list when the field was not provided.
     if value is None:
         return []
 
     # Split on commas, normalize each part, and deduplicate.
     normalized_items = []
     for raw_part in value.split(","):
         normalized_part = _normalize_text(raw_part)
         if normalized_part is not None and normalized_part not in normalized_items:
             normalized_items.append(normalized_part)
 
     # Log the result for debugging.
     logger.debug("📝 Split CSV field '%s' → %d unique items: %s.", value, len(normalized_items), normalized_items)
     return normalized_items
 
 
 # ═════════════════════════════════════════════════════════════════════════════
 #  HELPER: Build the shared NormalizedUserContext from multipart form fields.
 #
 #  WHY THIS EXISTS:
 #  ────────────────
 #  Both endpoints (/images/analyze and /outfits/recommend) accept the same
 #  set of user context fields (occasion, weather, gender, etc.). This helper
 #  avoids duplicating the normalization logic by building a single typed
 #  NormalizedUserContext object from the raw form field values.
 #
 #  HOW IT WORKS:
 #  ─────────────
 #  1. Log all incoming field values for traceability.
 #  2. Normalize each text field using _normalize_text().
 #  3. Split comma-separated fields using _split_csv_field().
 #  4. Build and return a NormalizedUserContext Pydantic model.
 # ═════════════════════════════════════════════════════════════════════════════
def _build_context(
     user_id: str | None,
     gender: str | None,
     occasion: str | None,
     weather: str | None,
     temperature_celsius: float | None,
     dress_code: str | None,
     style_preferences: str | None,
     color_preferences: str | None,
     avoid_items: str | None,
 ) -> NormalizedUserContext:
     """Build the normalized context model used by both endpoints.
 
     This function takes raw form field values from the HTTP request and
     converts them into a clean, consistent NormalizedUserContext object.
     All text is lowercased, trimmed, and deduplicated.
 
     Args:
         user_id:              Optional user tracking identifier.
         gender:               User's gender (e.g. "male", "female", "non-binary").
         occasion:             Target occasion (e.g. "office", "party", "beach").
         weather:              Current weather description (e.g. "rainy", "sunny").
         temperature_celsius:  Ambient temperature as a number (e.g. 22.5).
         dress_code:           Dress code constraint (e.g. "business casual").
         style_preferences:    Comma-separated style tags (e.g. "minimal, classic").
         color_preferences:    Comma-separated color names (e.g. "navy, charcoal").
         avoid_items:          Comma-separated items to exclude (e.g. "shorts, tie").
 
     Returns:
         A fully normalized NormalizedUserContext ready for service consumption.
     """
 
     # Log every incoming field so the full request context is traceable in logs.
     logger.info("📋 Building user context from form fields:")
     logger.info("   • user_id=%s, gender=%s, occasion=%s", user_id, gender, occasion)
     logger.info("   • weather=%s, temperature=%s°C, dress_code=%s", weather, temperature_celsius, dress_code)
     if style_preferences:
         logger.info("   • style_preferences='%s'", style_preferences)
     if color_preferences:
         logger.info("   • color_preferences='%s'", color_preferences)
     if avoid_items:
         logger.info("   • avoid_items='%s'", avoid_items)
 
     # Build the typed context object with all fields normalized.
     ctx = NormalizedUserContext(
         User_id=_normalize_text(user_id),
         Gender=_normalize_text(gender),
         Occasion=_normalize_text(occasion),
         Weather=_normalize_text(weather),
         Temperature_celsius=temperature_celsius,
         Dress_code=_normalize_text(dress_code),
         Style_preferences=_split_csv_field(style_preferences),
         Color_preferences=_split_csv_field(color_preferences),
         Avoid_items=_split_csv_field(avoid_items),
     )
 
     # Log the final normalized context for verification.
     logger.info("📋 User context built successfully:")
     logger.info("   • occasion='%s', weather='%s', gender='%s'", ctx.Occasion, ctx.Weather, ctx.Gender)
     logger.info("   • %d style prefs, %d color prefs, %d avoid items",
                 len(ctx.Style_preferences), len(ctx.Color_preferences), len(ctx.Avoid_items))
     return ctx
 
 
 # ═════════════════════════════════════════════════════════════════════════════
 #  HELPER: Read and validate an uploaded image from a multipart request.
 #
 #  WHY THIS EXISTS:
 #  ────────────────
 #  Both endpoints accept image uploads. This helper centralizes all upload
 #  validation (MIME type check, emptiness check, file size check) so the
 #  endpoint handlers stay clean and focused on business logic.
 #
 #  VALIDATION CHAIN (in order):
 #  ────────────────────────────
 #  1. If no image was uploaded → return (None, None, None) — this is OK
 #     for /outfits/recommend where the image is optional.
 #  2. Check the MIME type starts with "image/" → 400 if not.
 #  3. Read the full file into memory.
 #  4. Check the file is not empty (0 bytes) → 400 if empty.
 #  5. Check the file size is within the configured limit → 413 if too large.
 #  6. Return (file_bytes, file_name, content_type) on success.
 #
 #  POSSIBLE HTTP ERRORS:
 #  ─────────────────────
 #  400 — File is not an image (wrong MIME type) or file is empty.
 #  413 — File exceeds the maximum upload size limit.
 # ═════════════════════════════════════════════════════════════════════════════
async def _read_optional_image(
     image: UploadFile | None,
     request_id: str = "unknown",
 ) -> tuple[bytes | None, str | None, str | None]:
     """Read an optional multipart image with size and MIME validation.
 
     Args:
         image:       The uploaded file from the multipart request, or None.
         request_id:  The unique request tracking ID for log correlation.
 
     Returns:
         A tuple of (file_bytes, file_name, content_type), or (None, None, None)
         if no image was uploaded.
 
     Raises:
         HTTPException 400: If the file is not an image or is empty.
         HTTPException 413: If the file exceeds the configured size limit.
     """
 
     # Load application settings to read the configured max upload size.
     settings = get_settings()
 
     # ── Check 1: Was an image uploaded at all? ───────────────────────────────
     if image is None:
         logger.info("[%s] 📤 No image was uploaded with this request — proceeding without an image.", request_id)
         return None, None, None
 
     logger.info("[%s] 📤 Image upload received — filename='%s', content_type='%s'.",
                 request_id, image.filename, image.content_type)
 
     # ── Check 2: Is the MIME type an image type? ─────────────────────────────
     # The browser or client reports the MIME type. We require it to start with
     # "image/" (e.g. image/jpeg, image/png, image/webp). If someone uploads a
     # PDF, text file, or video, this check catches it early.
     if image.content_type is None or not image.content_type.startswith("image/"):
         logger.warning("[%s] ❌ Rejected upload: content type '%s' is not an image MIME type.",
                        request_id, image.content_type)
         raise HTTPException(
             status_code=400,
             detail=f"Uploaded file must be an image (e.g. image/jpeg, image/png). "
                    f"Received content type: '{image.content_type}'.",
         )
 
     # ── Check 3: Read file bytes into memory ─────────────────────────────────
     # We read the entire file into memory so we can check its size and pass
     # the bytes downstream to the image processing pipeline.
     file_bytes = await image.read()
     await image.close()
 
     # ── Check 4: Is the file empty? ──────────────────────────────────────────
     if not file_bytes:
         logger.warning("[%s] ❌ Rejected upload: the file was empty (0 bytes).", request_id)
         raise HTTPException(
             status_code=400,
             detail="Uploaded image file is empty (0 bytes). Please upload a valid image.",
         )
 
     logger.info("[%s] 📤 Image read into memory — %d bytes (%.2f MB).",
                 request_id, len(file_bytes), len(file_bytes) / (1024 * 1024))
 
     # ── Check 5: Is the file within the size limit? ──────────────────────────
     # The maximum upload size is configured via the MAX_UPLOAD_SIZE_BYTES
     # environment variable (default: 15 MB). This prevents excessively large
     # files from consuming too much memory or processing time.
     if len(file_bytes) > settings.max_upload_size_bytes:
         max_mb = settings.max_upload_size_bytes / (1024 * 1024)
         actual_mb = len(file_bytes) / (1024 * 1024)
         logger.warning("[%s] ❌ Rejected upload: file size %.2f MB exceeds the limit of %.1f MB.",
                        request_id, actual_mb, max_mb)
         raise HTTPException(
             status_code=413,
             detail=f"Uploaded image is too large ({actual_mb:.2f} MB). "
                    f"Maximum allowed size is {max_mb:.1f} MB.",
         )
 
     # ── All checks passed ────────────────────────────────────────────────────
     logger.info("[%s] ✅ Image upload validated — filename='%s', size=%d bytes, type='%s'.",
                 request_id, image.filename, len(file_bytes), image.content_type)
     return file_bytes, image.filename or "uploaded-image", image.content_type
 
 
 # ═════════════════════════════════════════════════════════════════════════════
 #                    ENDPOINT 1: HEALTH CHECK
 #
 #  PURPOSE:
 #  ────────
 #  A simple "are you alive?" endpoint used by load balancers, Kubernetes
 #  readiness/liveness probes, and monitoring dashboards. It confirms the
 #  Python process is running and can handle HTTP requests.
 #
 #  WHAT IT DOES NOT CHECK:
 #  ───────────────────────
 #  • It does NOT check if the AI model is loaded (that happens lazily).
 #  • It does NOT check database connections (this service has no database).
 #  • It does NOT check disk space or memory.
 #
 #  RESPONSES:
 #  ──────────
 #  200 OK — {"status": "healthy", "service": "fashionpedia-api"}
 #
 #  This endpoint has no failure modes — it always returns 200 if the process
 #  is alive and can handle HTTP traffic.
 # ═════════════════════════════════════════════════════════════════════════════
@router.get(
     "/health",
     summary="Health check — is the service alive?",
     description=(
         "Returns a simple status object confirming the service is running. "
         "Used by load balancers and monitoring tools. Does NOT verify the AI model."
     ),
     response_description="Service is alive and healthy.",
     responses={
         200: {
             "description": "Service is running and healthy.",
             "content": {
                 "application/json": {
                     "example": {"status": "healthy", "service": "fashionpedia-api"}
                 }
             },
         },
     },
 )
async def health_check() -> dict:
     """Return a lightweight health-check response.
 
     This endpoint is intentionally minimal — no dependencies, no I/O, no model
     loading. It simply returns a static JSON object to prove the process is alive.
 
     Returns:
         A dict with "status" and "service" keys.
     """
 
     logger.info("💓 Health check endpoint was called — confirming the service is alive.")
     logger.info("✅ Health check passed — returning status 'healthy'.")
     return {"status": "healthy", "service": "fashionpedia-api"}


@router.get(
    "/ping",
    summary="Ping test — is the API reachable?",
    description=(
        "A lightweight endpoint for mobile apps to verify the network path to "
        "the API is working before sending larger requests."
    ),
    response_description="Service is reachable.",
    responses={
        200: {
            "description": "The service is reachable and responding.",
            "content": {
                "application/json": {
                    "example": {"status": "pong", "service": "fashionpedia-api"}
                }
            },
        },
    },
)
async def ping() -> dict:
    """Return a minimal reachable response for client connectivity tests."""

    logger.info("🏓 Ping endpoint called — returning pong.")
    return {"status": "pong", "service": "fashionpedia-api"}


@router.get(
    "/info",
    summary="Service info — app metadata and configuration.",
    description=(
        "Returns service metadata and configuration hints for mobile clients."
    ),
    response_description="Service metadata response.",
    responses={
        200: {
            "description": "Service metadata is returned.",
            "content": {
                "application/json": {
                    "example": {
                        "service": "fashionpedia-api",
                        "app_name": "Fashionpedia Outfit APIs",
                        "app_version": "1.0.0",
                        "model": "valentinafevu/yolos-fashionpedia",
                        "device": "auto",
                    }
                }
            },
        },
    },
)
async def info() -> dict:
    """Return application metadata for client verification."""

    settings = get_settings()
    logger.info("ℹ️  Service info endpoint called.")
    return {
        "service": "fashionpedia-api",
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "api_prefix": settings.api_prefix,
        "model": settings.fashionpedia_model_name,
        "device": settings.model_device,
        "warm_model_on_startup": settings.warm_model_on_startup,
    }


# ═════════════════════════════════════════════════════════════════════════════
#                    ENDPOINT 2: IMAGE ANALYSIS
 #
 #  ═══════════════════════════════════════════════════════════════════════════
 #  HIGH-LEVEL FLOW:
 #  ═══════════════════════════════════════════════════════════════════════════
 #
 #  Client ──POST /images/analyze──▶ routes.py (this file)
 #    │
 #    ├─ 1. Generate unique request ID for log correlation
 #    ├─ 2. _read_optional_image()  → validate upload (MIME, size, emptiness)
 #    ├─ 3. _build_context()        → normalize all text fields
 #    ├─ 4. service.analyze_image() → hand off to ImageAnalysisService
 #    └─ 5. Return AnalyzeImageResponse JSON to client
 #
 #  ═══════════════════════════════════════════════════════════════════════════
 #  LOW-LEVEL FLOW (inside ImageAnalysisService.analyze_image):
 #  ═══════════════════════════════════════════════════════════════════════════
 #
 #    Step 1: open_image_from_bytes()     → Decode raw bytes into a Pillow
 #            Image object. If the bytes are corrupted, raises ValueError.
 #
 #    Step 2: compute_sha256()            → Compute a unique fingerprint of
 #            the file for deduplication and audit trails.
 #
 #    Step 3: build_technical_metadata()  → Extract image dimensions, aspect
 #            ratio, orientation, megapixels, color mode, alpha channel,
 #            animation frames, ICC profile, DPI, and EXIF summary.
 #
 #    Step 4: build_quality_metadata()    → Analyze brightness (mean grayscale),
 #            contrast (std dev), entropy, sharpness (Laplacian variance),
 #            edge density (Canny), extract dominant colors (median-cut
 #            quantization), and generate quality warnings.
 #
 #    Step 5: detector.detect()           → Load YOLOS model (lazy, thread-safe),
 #            preprocess image, run AI inference, post-process raw outputs,
 #            filter by confidence threshold, map IDs → category names,
 #            extract crop color palettes per detected item.
 #
 #    Step 6: _build_outfit_breakdown()   → Group detections into body zones:
 #            upper body, lower body, one-piece, outerwear, footwear,
 #            accessories, garment parts, closures, decorations.
 #
 #    Step 7: _predict_context_fit()      → Score labels against 8 style
 #            signal sets, compare against user's occasion/weather, produce
 #            alignment scores and human-readable reasoning.
 #
 #  ═══════════════════════════════════════════════════════════════════════════
 #  ALL POSSIBLE RESPONSES:
 #  ═══════════════════════════════════════════════════════════════════════════
 #
 #  200 OK                  — Analysis completed successfully. Full JSON body.
 #  400 Bad Request         — Invalid upload (wrong MIME, empty file, corrupt
 #                            image bytes that cannot be decoded).
 #  413 Payload Too Large   — Image file exceeds the configured max size.
 #  422 Unprocessable Entity — FastAPI validation failed (e.g. missing required
 #                            "image" field, wrong data type for temperature).
 #  500 Internal Server Error — Unexpected crash during processing.
 #  503 Service Unavailable — AI model could not be loaded (missing deps,
 #                            network error downloading model weights, etc.).
 # ═════════════════════════════════════════════════════════════════════════════
@router.post(
     "/images/analyze",
     response_model=AnalyzeImageResponse,
     summary="Analyze an uploaded fashion image using the Fashionpedia AI model",
     description=(
         "Upload a fashion image (JPEG, PNG, WebP, etc.) and receive a comprehensive "
         "analysis including: file metadata, technical metadata (dimensions, EXIF), "
         "quality metrics (brightness, sharpness, dominant colors), AI-detected "
         "clothing items with bounding boxes and per-item color palettes, a grouped "
         "outfit breakdown by body zone, and a context-fit prediction that evaluates "
         "how well the outfit matches the requested occasion and weather."
     ),
     response_description="Full image analysis with metadata, detections, and style prediction.",
     responses={
         # ── 200: Success ─────────────────────────────────────────────────────
         200: {
             "description": (
                 "Image analysis completed successfully. The response includes "
                 "file metadata, technical metadata, quality metrics, AI detections, "
                 "outfit breakdown, label/supercategory counts, and context-fit prediction."
             ),
         },
         # ── 400: Bad Request ─────────────────────────────────────────────────
         400: {
             "description": (
                 "The request was invalid. Possible reasons:\n"
                 "• The uploaded file is not an image (wrong MIME type like application/pdf).\n"
                 "• The uploaded image file is empty (0 bytes).\n"
                 "• The image bytes are corrupted and cannot be decoded by the image library.\n"
             ),
             "model": ErrorResponse,
             "content": {
                 "application/json": {
                     "example": {
                         "status_code": 400,
                         "error": "invalid_image",
                         "detail": "Uploaded file is not a valid image. The file may be corrupted.",
                         "request_id": "a1b2c3d4",
                     }
                 }
             },
         },
         # ── 413: Payload Too Large ───────────────────────────────────────────
         413: {
             "description": (
                 "The uploaded image file exceeds the maximum allowed size "
                 "(default: 15 MB, configurable via MAX_UPLOAD_SIZE_BYTES env var)."
             ),
             "model": ErrorResponse,
             "content": {
                 "application/json": {
                     "example": {
                         "status_code": 413,
                         "error": "file_too_large",
                         "detail": "Uploaded image is too large (18.50 MB). Maximum allowed size is 15.0 MB.",
                         "request_id": "e5f6g7h8",
                     }
                 }
             },
         },
         # ── 422: Unprocessable Entity ───────────────────��────────────────────
         422: {
             "description": (
                 "FastAPI's automatic request validation failed. This happens when:\n"
                 "• The required 'image' file field is missing from the multipart form.\n"
                 "• A form field has the wrong data type (e.g. 'abc' for temperature_celsius).\n"
                 "FastAPI generates this response automatically; we do NOT need to raise it manually."
             ),
         },
         # ── 500: Internal Server Error ───────────────────────────────────────
         500: {
             "description": (
                 "An unexpected internal error occurred during processing. "
                 "The error details are logged server-side but not exposed to the client "
                 "for security reasons. Contact support with the request_id."
             ),
             "model": ErrorResponse,
             "content": {
                 "application/json": {
                     "example": {
                         "status_code": 500,
                         "error": "internal_error",
                         "detail": "An unexpected internal error occurred. Please try again or contact support.",
                         "request_id": "i9j0k1l2",
                     }
                 }
             },
         },
         # ── 503: Service Unavailable ─────────────────────────────────────────
         503: {
             "description": (
                 "The AI fashion detection model could not be loaded. Possible causes:\n"
                 "• Required ML libraries (torch, transformers) are not installed.\n"
                 "• Model weights failed to download from Hugging Face Hub.\n"
                 "• Insufficient memory to load the model.\n"
                 "The client should retry the request after some time."
             ),
             "model": ErrorResponse,
             "content": {
                 "application/json": {
                     "example": {
                         "status_code": 503,
                         "error": "model_unavailable",
                         "detail": "The AI fashion detection model is not available. Please try again later.",
                         "request_id": "m3n4o5p6",
                     }
                 }
             },
         },
     },
 )

async def analyze_image(
     # ── Required: The image file to analyze ──────────────────────────────────
     image: UploadFile = File(
         ...,
         description="Fashion image to analyze. Supported formats: JPEG, PNG, WebP, BMP, TIFF, GIF.",
     ),
     # ── Optional: User context fields ────────────────────────────────────────
     user_id: str | None = Form(default=None, description="Optional user identifier for request tracking and analytics."),
     gender: str | None = Form(default=None, description="User's gender (e.g. male, female, non-binary). Influences style scoring."),
     occasion: str | None = Form(default=None, description="Target occasion (e.g. office, party, beach, wedding). Used for context-fit prediction."),
     weather: str | None = Form(default=None, description="Current weather description (e.g. rainy, sunny, cold, hot). Used for weather alignment scoring."),
     temperature_celsius: float | None = Form(default=None, description="Ambient temperature in degrees Celsius (e.g. 22.5). Used to infer weather band."),
     dress_code: str | None = Form(default=None, description="Dress code constraint (e.g. business casual, formal, smart casual)."),
     style_preferences: str | None = Form(default=None, description="Comma-separated style tags (e.g. 'minimal, classic, streetwear')."),
     color_preferences: str | None = Form(default=None, description="Comma-separated preferred colors (e.g. 'navy, charcoal')."),
     avoid_items: str | None = Form(default=None, description="Comma-separated clothing items to avoid (e.g. 'shorts, tie, hat')."),
     # ── Injected: Service dependency ─────────────────────────────────────────
     service: ImageAnalysisService = Depends(get_image_analysis_service),
 ) -> AnalyzeImageResponse:
     """Accept an uploaded image and return detailed metadata plus AI detections.
 
     This is the primary analysis endpoint. It runs the full 7-step pipeline:
     image decoding → file metadata → technical metadata → quality analysis →
     AI detection → outfit grouping → context-fit prediction.
 
     The response includes everything a client needs to understand the image:
     what clothing items are in it, where they are located (bounding boxes),
     what colors they are, and how well the outfit fits the user's context.
     """
 
     # ── Generate a unique request ID ─────────────────────────────────────────
     # This 8-character ID appears in every log line for this request, making
     # it easy to search logs and trace the entire request lifecycle.
     request_id = str(uuid.uuid4())[:8]
 
     # Record the start time so we can measure total request duration.
     start_time = time.time()
 
     logger.info("═══════════════════════════════════════════════════════════════")
     logger.info("🔍 [%s] NEW REQUEST: POST /images/analyze", request_id)
     logger.info("═══════════════════════════════════════════════════════════════")
 
     # ── Step 1: Read and validate the uploaded image file ────────────────────
     # This step checks: (a) MIME type is image/*, (b) file is not empty,
     # (c) file is within the size limit. Raises 400 or 413 on failure.
     logger.info("[%s] Step 1: Validating the uploaded image file...", request_id)
     try:
         file_bytes, file_name, content_type = await _read_optional_image(image, request_id)
     except HTTPException:
         # Re-raise HTTP exceptions from validation — they already have the
         # correct status code and error message.
         raise
     except Exception as exc:
         # If something truly unexpected happens during file reading (e.g.
         # network interruption on a streaming upload), catch it here.
         elapsed = time.time() - start_time
         logger.exception("[%s] ❌ Unexpected error reading the uploaded file after %.2fs.", request_id, elapsed)
         return _error_response(
             status_code=500,
             error="upload_read_error",
             detail="An unexpected error occurred while reading the uploaded file.",
             request_id=request_id,
         )
 
     # ── Step 2: Normalize user-supplied text fields ──────────────────────────
     # All text is lowercased, trimmed, and deduplicated so downstream code
     # can do simple string comparisons without worrying about casing.
     logger.info("[%s] Step 2: Normalizing user context fields...", request_id)
     context = _build_context(
         user_id=user_id, gender=gender, occasion=occasion, weather=weather,
         temperature_celsius=temperature_celsius, dress_code=dress_code,
         style_preferences=style_preferences, color_preferences=color_preferences,
         avoid_items=avoid_items,
     )
 
     # ── Step 3: Hand off to the ImageAnalysisService ─────────────────────────
     # This runs the full 7-step pipeline: decode → metadata → quality →
     # AI detection → grouping → style prediction.
     try:
         logger.info("[%s] Step 3: 🚀 Handing off to ImageAnalysisService — running the full analysis pipeline...", request_id)
         result = service.analyze_image(
             file_bytes=file_bytes or b"",
             file_name=file_name or "uploaded-image",
             content_type=content_type or "image/unknown",
             context=context,
         )
 
         # ── Step 4: Log success summary and return ───────────────────────────
         elapsed = time.time() - start_time
         logger.info("[%s] ═══════════════════════════════════════════════════════", request_id)
         logger.info("[%s] ✅ /images/analyze completed successfully in %.2fs", request_id, elapsed)
         logger.info("[%s]    • %d fashion item(s) detected by the AI model", request_id, len(result.Fashionpedia_detections))
         logger.info("[%s]    • Predicted style: '%s'", request_id, result.Outfit_prediction.Predicted_style_label)
         logger.info("[%s]    • Occasion alignment: '%s'", request_id, result.Outfit_prediction.Occasion_alignment)
         logger.info("[%s]    • Weather alignment: '%s'", request_id, result.Outfit_prediction.Weather_alignment)
         logger.info("[%s]    • Confidence: %.1f%%", request_id, result.Outfit_prediction.Confidence * 100)
         logger.info("[%s]    • Quality warnings: %s", request_id, result.Quality_metadata.Quality_warnings or "(none)")
         logger.info("[%s] ═══════════════════════════════════════════════════════", request_id)
         return result
 
     # ── Handle: ValueError → 400 Bad Request ─────────────────────────────────
     # ValueError is raised by the service when the image bytes cannot be
     # decoded (e.g. the file is corrupted, truncated, or not actually an image
     # despite having an image/* MIME type).
     except ValueError as exc:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /images/analyze failed in %.2fs — image validation error: %s", request_id, elapsed, exc)
         return _error_response(
             status_code=400,
             error="invalid_image",
             detail=str(exc),
             request_id=request_id,
         )
 
     # ── Handle: RuntimeError → 503 Service Unavailable ───────────────────────
     # RuntimeError is raised by the detector when the AI model cannot be loaded
     # (e.g. missing torch/transformers packages, failed model download, out of
     # memory). This is a transient error — the client should retry later.
     except RuntimeError as exc:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /images/analyze failed in %.2fs — AI model error: %s", request_id, elapsed, exc)
         return _error_response(
             status_code=503,
             error="model_unavailable",
             detail=f"The AI fashion detection model is not available: {exc}",
             request_id=request_id,
         )
 
     # ── Handle: MemoryError → 503 Service Unavailable ────────────────────────
     # MemoryError can happen if the image is extremely large (e.g. a 50MP photo)
     # and the server runs out of RAM during processing.
     except MemoryError:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /images/analyze failed in %.2fs — server ran out of memory.", request_id, elapsed)
         return _error_response(
             status_code=503,
             error="out_of_memory",
             detail="The server ran out of memory while processing this image. Try uploading a smaller image.",
             request_id=request_id,
         )
 
     # ── Handle: TimeoutError → 503 Service Unavailable ───────────────────────
     # TimeoutError can happen if model inference takes too long (e.g. on a very
     # slow CPU with a very large image).
     except TimeoutError:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /images/analyze timed out after %.2fs.", request_id, elapsed)
         return _error_response(
             status_code=503,
             error="processing_timeout",
             detail="Image analysis timed out. Try uploading a smaller or simpler image.",
             request_id=request_id,
         )
 
     # ── Handle: OSError → 500 Internal Server Error ──────────────────────────
     # OSError can happen if there are disk I/O issues (e.g. reading the catalog
     # file, temporary file operations) or GPU driver errors.
     except OSError as exc:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /images/analyze failed in %.2fs — OS/IO error: %s", request_id, elapsed, exc)
         return _error_response(
             status_code=500,
             error="io_error",
             detail="A system-level I/O error occurred during image processing.",
             request_id=request_id,
         )
 
     # ── Handle: Any other exception → 500 Internal Server Error ──────────────
     # This is the catch-all safety net. Any exception not caught above ends up
     # here. We log the full stack trace for debugging but return a generic
     # error message to the client so internal details are not leaked.
     except Exception as exc:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /images/analyze failed in %.2fs — unexpected error: %s", request_id, elapsed, type(exc).__name__)
         logger.error("[%s] Full stack trace:\n%s", request_id, traceback.format_exc())
         return _error_response(
             status_code=500,
             error="internal_error",
             detail="An unexpected internal error occurred. Please try again or contact support.",
             request_id=request_id,
         )
 
 
 # ═════════════════════════════════════════════════════════════════════════════
 #                    ENDPOINT 3: OUTFIT RECOMMENDATION
 #
 #  ═══════════════════════════════════════════════════════════════════════════
 #  HIGH-LEVEL FLOW:
 #  ═══════════════════════════════════════════════════════════════════════════
 #
 #  Client ──POST /outfits/recommend──▶ routes.py (this file)
 #    │
 #    ├─ 1. Generate unique request ID for log correlation
 #    ├─ 2. _read_optional_image()       → validate optional reference image
 #    ├─ 3. _build_context()             → normalize all text fields
 #    ├─ 4. service.recommend()          → hand off to OutfitRecommender
 #    └─ 5. Return RecommendOutfitResponse JSON to client
 #
 #  ═══════════════════════════════════════════════════════════════════════════
 #  LOW-LEVEL FLOW (inside OutfitRecommender.recommend):
 #  ═══════════════════════════════════════════════════════════════════════════
 #
 #    Step 1: _normalize_occasion_bucket() → Map free-form occasion text to
 #            one of 8 buckets: office, formal, party, festive, sport,
 #            travel, beach, casual. Uses keyword matching.
 #
 #    Step 2: _infer_weather_band() → Map weather text + temperature to one
 #            of 6 bands: cold, cool, mild, warm, hot, rainy.
 #            Priority: rain keywords > temperature number > weather keywords.
 #
 #    Step 3: (Optional) _summarize_reference_image() → If a reference image
 #            was uploaded, run the AI detector on it, extract detected labels
 #            and dominant colors, infer a style label (formal, party, casual).
 #
 #    Step 4: _score_template() × 11 → Score each curated template against
 #            the user's context:
 #            • +6.0 points if occasion bucket matches exactly
 #            • +3.5 points for close occasion matches (office↔formal)
 #            • +4.0 points if weather band matches exactly
 #            • +2.5 points for partial weather matches (rain + umbrella)
 #            • +0.5 points for gender-appropriate items
 #            • +0.4 per reference image label overlap
 #            • +0.2 per style preference keyword match
 #            • −2.0 per avoided item in primary items
 #            • −1.0 per avoided item in optional items
 #
 #    Step 5: Sort templates by score, select top N (default: 3).
 #
 #    Step 6: Personalize each selected template:
 #            • Replace avoided items with fallback alternatives
 #            • Add weather-specific items (umbrella for rain, scarf for cold)
 #            • Remove inappropriate items (coat in hot weather)
 #            • Apply user's color preferences or reference image colors
 #
 #    Step 7: Build final OutfitRecommendation objects with reasoning strings,
 #            confidence scores, attribute-direction hints, and assemble the
 #            RecommendOutfitResponse with deprioritized items and notes.
 #
 #  ═══════════════════════════════════════════════════════════════════════════
 #  ALL POSSIBLE RESPONSES:
 #  ═══════════════════════════════════════════════════════════════════════════
 #
 #  200 OK                  — Recommendations generated successfully.
 #  400 Bad Request         — Invalid reference image (wrong MIME, empty,
 #                            corrupted bytes), or other validation error.
 #  413 Payload Too Large   — Reference image exceeds max file size.
 #  422 Unprocessable Entity — FastAPI validation failed (e.g. missing required
 #                            "occasion" field, wrong type for temperature).
 #  500 Internal Server Error — Unexpected crash during processing.
 #  503 Service Unavailable — AI model not available (only relevant when a
 #                            reference image is uploaded and needs analysis).
 # ═════════════════════════════════════════════════════════════════════════════
@router.post(
     "/outfits/recommend",
     response_model=RecommendOutfitResponse,
     summary="Get personalized outfit recommendations based on occasion, weather, and preferences",
     description=(
         "Provide an occasion (required), optional weather/temperature, optional style "
         "and color preferences, optional items to avoid, and an optional reference image "
         "to receive personalized outfit recommendations. Each recommendation includes "
         "primary clothing items, optional accessories, color palette suggestions, "
         "Fashionpedia attribute-direction hints, and human-readable reasoning explaining "
         "why the outfit was chosen."
     ),
     response_description="Ranked outfit recommendations with reasoning and metadata.",
     responses={
         # ── 200: Success ─────────────────────────────────────────────────────
         200: {
             "description": (
                 "Outfit recommendations generated successfully. The response includes "
                 "the normalized user context, optional reference image summary, ranked "
                 "recommendations with items/colors/reasoning, and deprioritized items."
             ),
         },
         # ── 400: Bad Request ──────��──────────────────────────────────────────
         400: {
             "description": (
                 "The request was invalid. Possible reasons:\n"
                 "• The optional reference image is not an image (wrong MIME type).\n"
                 "• The optional reference image is empty (0 bytes).\n"
                 "• The reference image bytes are corrupted and cannot be decoded.\n"
             ),
             "model": ErrorResponse,
             "content": {
                 "application/json": {
                     "example": {
                         "status_code": 400,
                         "error": "invalid_image",
                         "detail": "Uploaded file is not a valid image. The file may be corrupted.",
                         "request_id": "q7r8s9t0",
                     }
                 }
             },
         },
         # ── 413: Payload Too Large ───────────────────────────────────────────
         413: {
             "description": "The optional reference image exceeds the maximum allowed size.",
             "model": ErrorResponse,
             "content": {
                 "application/json": {
                     "example": {
                         "status_code": 413,
                         "error": "file_too_large",
                         "detail": "Uploaded image is too large (20.00 MB). Maximum allowed size is 15.0 MB.",
                         "request_id": "u1v2w3x4",
                     }
                 }
             },
         },
         # ── 422: Unprocessable Entity ────────────────────────────────────────
         422: {
             "description": (
                 "FastAPI validation failed. Most common cause: the required 'occasion' "
                 "form field is missing from the request."
             ),
         },
         # ── 500: Internal Server Error ───────────────────────────────────────
         500: {
             "description": "An unexpected internal error occurred during recommendation generation.",
             "model": ErrorResponse,
             "content": {
                 "application/json": {
                     "example": {
                         "status_code": 500,
                         "error": "internal_error",
                         "detail": "An unexpected internal error occurred. Please try again or contact support.",
                         "request_id": "y5z6a7b8",
                     }
                 }
             },
         },
         # ── 503: Service Unavailable ─────────────────────────────────────────
         503: {
             "description": (
                 "The AI model is not available. This only applies when a reference image "
                 "is uploaded and the detector cannot load. Without a reference image, "
                 "this endpoint does not need the AI model."
             ),
             "model": ErrorResponse,
             "content": {
                 "application/json": {
                     "example": {
                         "status_code": 503,
                         "error": "model_unavailable",
                         "detail": "The AI model is not available for reference image analysis. Try again later.",
                         "request_id": "c9d0e1f2",
                     }
                 }
             },
         },
     },
 )
async def recommend_outfit(
     # ── Required: The target occasion ────────────────────────────────────────
     occasion: str = Form(
         ...,
         description="Target occasion (required). Examples: office, party, beach, sport, wedding, travel, formal.",
     ),
     # ── Optional: Reference image ────────────────────────────────────────────
     image: UploadFile | None = File(
         default=None,
         description="Optional reference image to influence style. The AI detector will analyze it for style cues.",
     ),
     # ── Optional: User context fields ────────────────────────────────────────
     user_id: str | None = Form(default=None, description="Optional user identifier for request tracking."),
     gender: str | None = Form(default=None, description="User's gender (e.g. male, female, non-binary). Influences item selection."),
     weather: str | None = Form(default=None, description="Current weather description (e.g. rainy, sunny, cold). Influences layering and accessories."),
     temperature_celsius: float | None = Form(default=None, description="Ambient temperature in °C (e.g. 22.5). Used to infer weather band."),
     dress_code: str | None = Form(default=None, description="Dress code constraint (e.g. business casual, formal)."),
     style_preferences: str | None = Form(default=None, description="Comma-separated style tags (e.g. 'minimal, classic')."),
     color_preferences: str | None = Form(default=None, description="Comma-separated preferred colors (e.g. 'navy, charcoal')."),
     avoid_items: str | None = Form(default=None, description="Comma-separated items to avoid (e.g. 'shorts, tie'). These will be swapped or removed."),
     # ── Injected: Service dependency ─────────────────────────────────────────
     service: OutfitRecommender = Depends(get_outfit_recommender),
 ) -> RecommendOutfitResponse:
     """Recommend outfits from metadata and an optional reference image.
 
     This endpoint does NOT require an image upload. It uses the user's text
     context (occasion, weather, preferences) to select and personalize outfit
     templates from the Fashionpedia ontology. If a reference image is provided,
     the AI detector analyzes it for style cues that nudge the recommendations.
 
     The response includes ranked outfit recommendations, each with:
     • Primary clothing items (e.g. shirt, pants, shoe)
     • Optional accessories (e.g. watch, belt, bag)
     • Style details (e.g. collar, lapel, pocket)
     • Attribute-direction hints (e.g. "plain pattern", "straight silhouette")
     • Color palette suggestions
     • Human-readable reasoning explaining why the outfit was chosen
     """
 
     # ── Generate a unique request ID ─────────────────────────────────────────
     request_id = str(uuid.uuid4())[:8]
     start_time = time.time()
 
     logger.info("═══════════════════════════════════════════════════════════════")
     logger.info("👗 [%s] NEW REQUEST: POST /outfits/recommend", request_id)
     logger.info("   Occasion: '%s'", occasion)
     logger.info("   Reference image: %s", "yes" if image else "no")
     logger.info("═══════════════════════════════════════════════════��═══════════")
 
     # ── Step 1: Read and validate the optional reference image ───────────────
     logger.info("[%s] Step 1: Checking for an optional reference image...", request_id)
     try:
         file_bytes, _, _ = await _read_optional_image(image, request_id)
     except HTTPException:
         raise
     except Exception as exc:
         elapsed = time.time() - start_time
         logger.exception("[%s] ❌ Unexpected error reading the reference image after %.2fs.", request_id, elapsed)
         return _error_response(
             status_code=500,
             error="upload_read_error",
             detail="An unexpected error occurred while reading the reference image.",
             request_id=request_id,
         )
 
     # ── Step 2: Normalize user-supplied text fields ──────────────────────────
     logger.info("[%s] Step 2: Normalizing user context fields...", request_id)
     context = _build_context(
         user_id=user_id, gender=gender, occasion=occasion, weather=weather,
         temperature_celsius=temperature_celsius, dress_code=dress_code,
         style_preferences=style_preferences, color_preferences=color_preferences,
         avoid_items=avoid_items,
     )
 
     # ── Step 3: Hand off to the OutfitRecommender ────────────────────────────
     try:
         logger.info("[%s] Step 3: 🚀 Handing off to OutfitRecommender — generating outfit suggestions...", request_id)
         result = service.recommend(context=context, reference_image_bytes=file_bytes)
 
         # ── Step 4: Log success summary and return ───────────────────────────
         elapsed = time.time() - start_time
         logger.info("[%s] ═══════════════════════════════════════════════════════", request_id)
         logger.info("[%s] ✅ /outfits/recommend completed successfully in %.2fs", request_id, elapsed)
         logger.info("[%s]    • %d outfit(s) recommended", request_id, len(result.Recommendations))
         for rec in result.Recommendations:
             logger.info("[%s]    • Rank #%d: '%s' (style: %s, confidence: %.0f%%)",
                         request_id, rec.Rank, rec.Title, rec.Style_label, rec.Confidence * 100)
             logger.info("[%s]      Primary items: %s", request_id, rec.Primary_items)
             logger.info("[%s]      Optional items: %s", request_id, rec.Optional_items)
             logger.info("[%s]      Palette: %s", request_id, rec.Palette_direction)
         if result.Deprioritized_items:
             logger.info("[%s]    • Deprioritized items: %s", request_id, result.Deprioritized_items)
         if result.Reference_image_summary:
             logger.info("[%s]    • Reference image style: '%s', labels: %s, colors: %s",
                         request_id,
                         result.Reference_image_summary.Predicted_style_label,
                         result.Reference_image_summary.Detected_categories[:5],
                         result.Reference_image_summary.Dominant_colors[:3])
         logger.info("[%s] ═══════════════════════════════════════════════════════", request_id)
         return result
 
     # ── Handle: ValueError → 400 Bad Request ─────────────────────────────────
     # Raised when the reference image bytes are corrupted or invalid.
     except ValueError as exc:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /outfits/recommend failed in %.2fs — validation error: %s", request_id, elapsed, exc)
         return _error_response(
             status_code=400,
             error="invalid_input",
             detail=str(exc),
             request_id=request_id,
         )
 
     # ── Handle: RuntimeError → 503 Service Unavailable ───────────────────────
     # Raised when the AI model cannot be loaded (only relevant when a reference
     # image is uploaded and the detector needs to run).
     except RuntimeError as exc:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /outfits/recommend failed in %.2fs — model error: %s", request_id, elapsed, exc)
         return _error_response(
             status_code=503,
             error="model_unavailable",
             detail=f"The AI model is not available: {exc}",
             request_id=request_id,
         )
 
     # ── Handle: MemoryError → 503 Service Unavailable ────────────────────────
     except MemoryError:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /outfits/recommend failed in %.2fs — out of memory.", request_id, elapsed)
         return _error_response(
             status_code=503,
             error="out_of_memory",
             detail="The server ran out of memory. Try without a reference image or with a smaller image.",
             request_id=request_id,
         )
 
     # ── Handle: TimeoutError → 503 Service Unavailable ───────────────────────
     except TimeoutError:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /outfits/recommend timed out after %.2fs.", request_id, elapsed)
         return _error_response(
             status_code=503,
             error="processing_timeout",
             detail="Recommendation generation timed out. Try without a reference image.",
             request_id=request_id,
         )
 
     # ── Handle: OSError → 500 Internal Server Error ──────────────────────────
     except OSError as exc:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /outfits/recommend failed in %.2fs — OS/IO error: %s", request_id, elapsed, exc)
         return _error_response(
             status_code=500,
             error="io_error",
             detail="A system-level I/O error occurred during recommendation generation.",
             request_id=request_id,
         )
 
     # ── Handle: Any other exception → 500 Internal Server Error ──────────────
     except Exception as exc:
         elapsed = time.time() - start_time
         logger.error("[%s] ❌ /outfits/recommend failed in %.2fs — unexpected error: %s", request_id, elapsed, type(exc).__name__)
         logger.error("[%s] Full stack trace:\n%s", request_id, traceback.format_exc())
         return _error_response(
             status_code=500,
             error="internal_error",
             detail="An unexpected internal error occurred. Please try again or contact support.",
             request_id=request_id,
         )