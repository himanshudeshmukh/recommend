from __future__ import annotations

"""Business logic for the `/images/analyze` endpoint.

╔══════════════════════════════════════════════════════════════════════════════╗
║                   IMAGE ANALYSIS SERVICE — ARCHITECTURE                    ║
║                                                                              ║
║  This service orchestrates the full image analysis pipeline. It is the      ║
║  "brain" behind the /images/analyze endpoint.                               ║
║                                                                              ║
║  PIPELINE (7 steps):                                                        ║
║  ───────────────────                                                        ║
║  Step 1: Decode uploaded bytes into a Pillow Image object                   ║
║  Step 2: Build file metadata (name, size, SHA-256 hash)                     ║
║  Step 3: Extract technical metadata (dimensions, EXIF, DPI, animation)      ║
║  Step 4: Analyze image quality (brightness, contrast, sharpness, colors)    ║
║  Step 5: Run the AI fashion detector (find clothing items + bounding boxes) ║
║  Step 6: Group detections into outfit categories                            ║
║  Step 7: Predict context fit (occasion/weather alignment)                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from collections import Counter
import logging
import time

from app.core.config import Settings
from app.models.schemas import (
    AnalyzeImageResponse,
    ContextFitPrediction,
    FileMetadata,
    NormalizedUserContext,
    OutfitBreakdown,
)
from app.services.fashionpedia_detector import FashionpediaDetector
from app.services.vision_utils import (
    build_quality_metadata,
    build_technical_metadata,
    compute_sha256,
    open_image_from_bytes,
)

logger = logging.getLogger(__name__)


class ImageAnalysisService:
    """High-level image analysis orchestrator."""

    OUTERWEAR_LABELS = {
        "jacket",
        "cardigan",
        "vest",
        "coat",
        "cape",
    }

    OFFICE_SIGNAL_LABELS = {
        "shirt, blouse",
        "jacket",
        "pants",
        "tie",
        "watch",
        "belt",
        "collar",
        "lapel",
    }

    FORMAL_SIGNAL_LABELS = {
        "tie",
        "jacket",
        "coat",
        "lapel",
        "collar",
    }

    CASUAL_SIGNAL_LABELS = {
        "top, t-shirt, sweatshirt",
        "pants",
        "shorts",
        "sweater",
        "cardigan",
        "jacket",
        "shoe",
        "hood",
        "pocket",
    }

    PARTY_SIGNAL_LABELS = {
        "dress",
        "jumpsuit",
        "bow",
        "flower",
        "ruffle",
        "sequin",
        "bead",
        "tassel",
        "ribbon",
    }

    SPORT_SIGNAL_LABELS = {
        "top, t-shirt, sweatshirt",
        "shorts",
        "shoe",
        "sock",
        "headband, head covering, hair accessory",
        "hood",
    }

    TRAVEL_SIGNAL_LABELS = {
        "jacket",
        "pants",
        "bag, wallet",
        "shoe",
        "glasses",
        "umbrella",
        "hood",
        "pocket",
        "zipper",
    }

    BEACH_SIGNAL_LABELS = {
        "shorts",
        "dress",
        "hat",
        "glasses",
        "scarf",
        "bag, wallet",
    }

    COLD_WEATHER_LABELS = {
        "sweater",
        "cardigan",
        "jacket",
        "coat",
        "cape",
        "scarf",
        "glove",
        "tights, stockings",
        "leg warmer",
    }

    HOT_WEATHER_LABELS = {
        "top, t-shirt, sweatshirt",
        "shorts",
        "dress",
        "hat",
        "glasses",
        "shoe",
    }

    def __init__(
        self,
        settings: Settings,
        detector: FashionpediaDetector,
    ) -> None:
        """Store shared dependencies."""

        self._settings = settings
        self._detector = detector

        logger.info(
            "ImageAnalysisService initialized with detector backend '%s'.",
            detector.backend_name,
        )

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────

    def analyze_image(
        self,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
        context: NormalizedUserContext,
    ) -> AnalyzeImageResponse:
        """Run the full image analysis pipeline."""

        pipeline_start = time.time()

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(
            "🖼️ Starting full image analysis for '%s' (%d bytes, type: %s).",
            file_name,
            len(file_bytes),
            content_type,
        )
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Step 1: Decode image
        logger.info("Step 1/7: Decoding uploaded image...")
        t0 = time.time()

        image = open_image_from_bytes(file_bytes)

        logger.info("   Step 1 done in %.3fs.", time.time() - t0)

        # Step 2: File metadata
        logger.info("Step 2/7: Building file metadata...")
        t0 = time.time()

        file_metadata = FileMetadata(
            File_name=file_name,
            Content_type=content_type,
            File_size_bytes=len(file_bytes),
            Sha256=compute_sha256(file_bytes),
        )

        logger.info(
            "   SHA256: %s... — done in %.3fs.",
            file_metadata.Sha256[:12],
            time.time() - t0,
        )

        # Step 3: Technical metadata
        logger.info("Step 3/7: Extracting technical metadata...")
        t0 = time.time()

        technical_metadata = build_technical_metadata(image)

        logger.info("   Step 3 done in %.3fs.", time.time() - t0)

        # Step 4: Quality metadata
        logger.info("Step 4/7: Building quality metadata...")
        t0 = time.time()

        quality_metadata = build_quality_metadata(
            image,
            top_k=self._settings.dominant_color_count,
        )

        logger.info("   Step 4 done in %.3fs.", time.time() - t0)

        # Step 5: AI detection
        logger.info("Step 5/7: Running AI fashion detector...")
        t0 = time.time()

        detections = self._detector.detect(image)

        logger.info(
            "   Detector found %d item(s) in %.3fs.",
            len(detections),
            time.time() - t0,
        )

        for index, detection in enumerate(detections):
            logger.info(
                "   Item %d: '%s' (%s) — confidence %.1f%%",
                index + 1,
                detection.Label,
                detection.Supercategory,
                detection.Confidence * 100,
            )

        # Step 6: Outfit breakdown
        logger.info("Step 6/7: Building outfit breakdown...")
        t0 = time.time()

        detected_outfit_summary = self._build_outfit_breakdown(detections)

        logger.info("   Step 6 done in %.3fs.", time.time() - t0)

        counts_by_label = dict(
            Counter(item.Label for item in detections)
        )

        counts_by_supercategory = dict(
            Counter(item.Supercategory for item in detections)
        )

        # Step 7: Context prediction
        logger.info("Step 7/7: Predicting context fit...")
        t0 = time.time()

        outfit_prediction = self._predict_context_fit(
            detections,
            context,
        )

        logger.info("   Step 7 done in %.3fs.", time.time() - t0)

        notes = [
            "The default detector returns Fashionpedia category detections and image metadata.",
            "For official Fashionpedia attribute_ids support, replace the backend with the official Attribute-Mask R-CNN pipeline.",
        ]

        total_elapsed = time.time() - pipeline_start

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(
            "✅ Image analysis completed in %.2fs.",
            total_elapsed,
        )
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return AnalyzeImageResponse(
            Context=context,
            File_metadata=file_metadata,
            Technical_metadata=technical_metadata,
            Quality_metadata=quality_metadata,
            Detector_backend=self._detector.backend_name,
            Detector_model_name=self._detector.model_name,
            Fashionpedia_detections=detections,
            Detected_outfit_summary=detected_outfit_summary,
            Counts_by_label=counts_by_label,
            Counts_by_supercategory=counts_by_supercategory,
            Outfit_prediction=outfit_prediction,
            Notes=notes,
        )

    # ──────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────

    def _append_unique(
        self,
        target: list[str],
        value: str,
    ) -> None:
        """Append only if missing."""

        if value not in target:
            target.append(value)

    def _build_outfit_breakdown(
        self,
        detections: list,
    ) -> OutfitBreakdown:
        """Group detections into outfit categories."""

        upper_body: list[str] = []
        lower_body: list[str] = []
        one_piece: list[str] = []
        outerwear: list[str] = []
        footwear: list[str] = []
        accessories: list[str] = []
        garment_parts: list[str] = []
        closures: list[str] = []
        decorations: list[str] = []

        for detection in detections:
            label = detection.Label
            supercategory = detection.Supercategory

            if supercategory == "upperbody":
                self._append_unique(upper_body, label)

                if label in self.OUTERWEAR_LABELS:
                    self._append_unique(outerwear, label)

            elif supercategory == "lowerbody":
                self._append_unique(lower_body, label)

            elif supercategory == "wholebody":
                self._append_unique(one_piece, label)

            elif supercategory == "shoe":
                self._append_unique(footwear, label)

            elif supercategory in {
                "head",
                "neck",
                "arms and hands",
                "waist",
                "legs and feet",
                "others",
            }:
                self._append_unique(accessories, label)

            elif supercategory == "garment parts":
                self._append_unique(garment_parts, label)

            elif supercategory == "closures":
                self._append_unique(closures, label)

            elif supercategory == "decorations":
                self._append_unique(decorations, label)

        return OutfitBreakdown(
            Upper_body=upper_body,
            Lower_body=lower_body,
            One_piece=one_piece,
            Outerwear=outerwear,
            Footwear=footwear,
            Accessories=accessories,
            Garment_parts=garment_parts,
            Closures=closures,
            Decorations=decorations,
        )

    def _normalize_text(
        self,
        value: str | None,
    ) -> str | None:
        """Normalize free-form text."""

        if value is None:
            return None

        normalized = " ".join(value.strip().lower().split())

        return normalized or None

    def _normalize_occasion_bucket(
        self,
        occasion: str | None,
    ) -> str | None:
        """Map free-form occasion text into a bucket."""

        normalized = self._normalize_text(occasion)

        if normalized is None:
            return None

        if any(
            token in normalized
            for token in {
                "office",
                "work",
                "business",
                "meeting",
                "corporate",
            }
        ):
            return "office"

        if any(
            token in normalized
            for token in {
                "formal",
                "black tie",
                "ceremony",
            }
        ):
            return "formal"

        if any(
            token in normalized
            for token in {
                "party",
                "cocktail",
                "night",
                "club",
                "date",
            }
        ):
            return "party"

        if any(
            token in normalized
            for token in {
                "wedding",
                "festival",
                "festive",
                "celebration",
            }
        ):
            return "festive"

        if any(
            token in normalized
            for token in {
                "sport",
                "gym",
                "workout",
                "training",
                "running",
            }
        ):
            return "sport"

        if any(
            token in normalized
            for token in {
                "travel",
                "airport",
                "trip",
                "journey",
            }
        ):
            return "travel"

        if any(
            token in normalized
            for token in {
                "beach",
                "resort",
                "vacation",
                "pool",
            }
        ):
            return "beach"

        return "casual"

    def _infer_weather_band(
        self,
        weather: str | None,
        temperature_celsius: float | None,
    ) -> str:
        """Infer weather band from user input."""

        normalized_weather = self._normalize_text(weather) or ""

        if any(
            token in normalized_weather
            for token in {"rain", "storm", "drizzle"}
        ):
            return "rainy"

        if temperature_celsius is not None:
            if temperature_celsius <= 10:
                return "cold"

            if temperature_celsius <= 20:
                return "cool"

            if temperature_celsius <= 29:
                return "warm"

            return "hot"

        if any(
            token in normalized_weather
            for token in {
                "snow",
                "cold",
                "winter",
                "freezing",
            }
        ):
            return "cold"

        if any(
            token in normalized_weather
            for token in {
                "cool",
                "chilly",
                "autumn",
            }
        ):
            return "cool"

        if any(
            token in normalized_weather
            for token in {
                "hot",
                "heat",
                "summer",
                "humid",
            }
        ):
            return "hot"

        if any(
            token in normalized_weather
            for token in {
                "warm",
                "sunny",
            }
        ):
            return "warm"

        return "mild"

    def _predict_context_fit(
        self,
        detections: list,
        context: NormalizedUserContext,
    ) -> ContextFitPrediction:
        """Predict outfit style and context alignment."""

        style_scores = {
            "casual": 0.0,
            "office": 0.0,
            "formal": 0.0,
            "party": 0.0,
            "sport": 0.0,
            "travel": 0.0,
            "beach": 0.0,
            "festive": 0.0,
        }

        cold_score = 0.0
        hot_score = 0.0

        reasoning: list[str] = []

        for detection in detections:
            label = detection.Label

            if label in self.CASUAL_SIGNAL_LABELS:
                style_scores["casual"] += 1.0

            if label in self.OFFICE_SIGNAL_LABELS:
                style_scores["office"] += 1.6

            if label in self.FORMAL_SIGNAL_LABELS:
                style_scores["formal"] += 1.6

            if label in self.PARTY_SIGNAL_LABELS:
                style_scores["party"] += 1.8
                style_scores["festive"] += 1.2

            if label in self.SPORT_SIGNAL_LABELS:
                style_scores["sport"] += 1.7

            if label in self.TRAVEL_SIGNAL_LABELS:
                style_scores["travel"] += 1.4

            if label in self.BEACH_SIGNAL_LABELS:
                style_scores["beach"] += 1.6

            if label in self.COLD_WEATHER_LABELS:
                cold_score += 1.5

            if label in self.HOT_WEATHER_LABELS:
                hot_score += 1.1

        predicted_style_label = max(
            style_scores,
            key=style_scores.get,
        )

        best_matching_occasion = predicted_style_label

        if style_scores[predicted_style_label] > 0:
            reasoning.append(
                f"Detected items most strongly match '{predicted_style_label}' styling cues."
            )

        if cold_score > hot_score + 1:
            reasoning.append(
                "Detected layers indicate cooler-weather dressing."
            )

        elif hot_score > cold_score + 1:
            reasoning.append(
                "Detected pieces suggest warm-weather dressing."
            )

        if not detections:
            reasoning.append(
                "No Fashionpedia items were detected."
            )

        requested_occasion = self._normalize_occasion_bucket(
            context.Occasion
        )

        requested_weather = self._infer_weather_band(
            context.Weather,
            context.Temperature_celsius,
        )

        occasion_alignment = "unknown"

        if requested_occasion is not None:
            if requested_occasion == best_matching_occasion:
                occasion_alignment = "good"

            elif {
                requested_occasion,
                best_matching_occasion,
            } <= {"office", "formal"}:
                occasion_alignment = "moderate"

            elif {
                requested_occasion,
                best_matching_occasion,
            } <= {"casual", "travel", "beach"}:
                occasion_alignment = "moderate"

            else:
                occasion_alignment = "poor"

        weather_alignment = "unknown"

        if requested_weather in {"cold", "cool"}:
            if cold_score >= 2:
                weather_alignment = "good"
            elif cold_score >= 1:
                weather_alignment = "moderate"
            else:
                weather_alignment = "poor"

        elif requested_weather in {"warm", "hot"}:
            if hot_score >= 2 and cold_score <= 2:
                weather_alignment = "good"
            elif hot_score >= 1:
                weather_alignment = "moderate"
            else:
                weather_alignment = "poor"

        elif requested_weather == "rainy":
            if any(
                item.Label in {
                    "umbrella",
                    "jacket",
                    "coat",
                    "hood",
                }
                for item in detections
            ):
                weather_alignment = "good"
            else:
                weather_alignment = "moderate"

        confidence = round(
            min(
                0.99,
                0.35
                + (
                    style_scores[predicted_style_label]
                    / max(len(detections) * 1.8, 1.0)
                ),
            ),
            4,
        )

        return ContextFitPrediction(
            Predicted_style_label=predicted_style_label,
            Best_matching_occasion=best_matching_occasion,
            Weather_alignment=weather_alignment,
            Occasion_alignment=occasion_alignment,
            Confidence=confidence,
            Reasoning=reasoning,
        )