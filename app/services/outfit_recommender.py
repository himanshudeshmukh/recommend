from __future__ import annotations

"""Business logic for the `/outfits/recommend` endpoint."""

from dataclasses import dataclass
import logging
from typing import Dict, List, Tuple

from app.core.config import Settings
from app.models.schemas import (
    AttributeDirection,
    NormalizedUserContext,
    OutfitRecommendation,
    RecommendOutfitResponse,
    ReferenceImageSummary,
)
from app.services.fashionpedia_catalog import FashionpediaCatalog
from app.services.fashionpedia_detector import FashionpediaDetector
from app.services.vision_utils import (
    extract_dominant_colors,
    open_image_from_bytes,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecommendationTemplate:
    """One curated recommendation template expressed in Fashionpedia labels."""

    title: str
    style_label: str
    occasions: Tuple[str, ...]
    weather_bands: Tuple[str, ...]
    primary_items: Tuple[str, ...]
    optional_items: Tuple[str, ...]
    style_details: Tuple[str, ...]
    attribute_direction: Dict[str, Tuple[str, ...]]
    palette_direction: Tuple[str, ...]


class OutfitRecommender:
    """Recommend outfits using the Fashionpedia category vocabulary."""

    AVOIDANCE_REPLACEMENTS = {
        "shorts": "pants",
        "dress": "jumpsuit",
        "jumpsuit": "dress",
        "jacket": "cardigan",
        "coat": "jacket",
        "scarf": "bag, wallet",
    }

    TEMPLATES = [
        RecommendationTemplate(
            title="Smart Office Layers",
            style_label="smart office",
            occasions=("office", "formal"),
            weather_bands=("cool", "cold", "mild", "rainy"),
            primary_items=("shirt, blouse", "pants", "jacket", "shoe"),
            optional_items=("watch", "belt", "bag, wallet", "umbrella"),
            style_details=("collar", "lapel"),
            attribute_direction={
                "textile pattern": ("plain (pattern)", "stripe"),
                "silhouette": ("straight",),
                "opening type": ("single breasted",),
            },
            palette_direction=("navy", "charcoal", "white", "beige"),
        ),
        RecommendationTemplate(
            title="Relaxed Summer Casual",
            style_label="summer casual",
            occasions=("casual", "travel", "beach"),
            weather_bands=("warm", "hot"),
            primary_items=("top, t-shirt, sweatshirt", "shorts", "shoe"),
            optional_items=("hat", "glasses", "bag, wallet"),
            style_details=("hood", "pocket"),
            attribute_direction={
                "textile pattern": ("plain (pattern)", "stripe"),
            },
            palette_direction=("white", "sky blue", "olive", "sand"),
        ),
    ]

    def __init__(
        self,
        settings: Settings,
        catalog: FashionpediaCatalog,
        detector: FashionpediaDetector,
    ) -> None:
        """Store shared dependencies."""

        self._settings = settings
        self._catalog = catalog
        self._detector = detector

    def _normalize_text(self, value: str | None) -> str | None:
        """Normalize free-form text."""

        if value is None:
            return None

        normalized = " ".join(value.strip().lower().split())
        return normalized or None

    def _normalize_occasion_bucket(self, occasion: str | None) -> str:
        """Map occasion text into a coarse bucket."""

        normalized = self._normalize_text(occasion) or "casual"

        if any(
            token in normalized
            for token in {"office", "work", "business", "meeting"}
        ):
            bucket = "office"

        elif any(
            token in normalized
            for token in {"formal", "black tie", "ceremony"}
        ):
            bucket = "formal"

        elif any(
            token in normalized
            for token in {"party", "cocktail", "night", "club"}
        ):
            bucket = "party"

        elif any(
            token in normalized
            for token in {"travel", "airport", "trip"}
        ):
            bucket = "travel"

        elif any(
            token in normalized
            for token in {"beach", "vacation", "pool"}
        ):
            bucket = "beach"

        else:
            bucket = "casual"

        logger.info(
            "Mapped occasion '%s' -> '%s'",
            occasion,
            bucket,
        )

        return bucket

    def _infer_weather_band(
        self,
        weather: str | None,
        temperature_celsius: float | None,
    ) -> str:
        """Infer weather bucket."""

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

        return "mild"

    def _unique(self, values: List[str]) -> List[str]:
        """Remove duplicates preserving order."""

        seen: list[str] = []

        for value in values:
            if value not in seen:
                seen.append(value)

        return seen

    def _replace_avoided_items(
        self,
        items: List[str],
        avoid_items: List[str],
    ) -> List[str]:
        """Replace avoided items."""

        resolved_items: list[str] = []

        for item in items:
            if item in avoid_items:
                replacement = self.AVOIDANCE_REPLACEMENTS.get(item)

                if replacement and replacement not in avoid_items:
                    resolved_items.append(replacement)

                continue

            resolved_items.append(item)

        return self._unique(resolved_items)

    def _build_attribute_direction(
        self,
        template: RecommendationTemplate,
    ) -> List[AttributeDirection]:
        """Build validated attribute directions."""

        directions: list[AttributeDirection] = []

        for supercategory, suggestions in template.attribute_direction.items():
            filtered = self._catalog.filter_known_attribute_names(
                list(suggestions)
            )

            if filtered:
                directions.append(
                    AttributeDirection(
                        supercategory=supercategory,
                        suggestions=filtered,
                    )
                )

        return directions

    def _infer_reference_style(
        self,
        labels: List[str],
    ) -> str | None:
        """Infer lightweight style label."""

        if not labels:
            return None

        if any(
            label in labels
            for label in {"tie", "jacket", "coat", "lapel"}
        ):
            return "formal"

        if any(
            label in labels
            for label in {"dress", "jumpsuit", "sequin"}
        ):
            return "party"

        if any(
            label in labels
            for label in {"shorts", "hat", "glasses"}
        ):
            return "summer casual"

        return "casual"

    def _summarize_reference_image(
        self,
        image_bytes: bytes,
    ) -> ReferenceImageSummary:
        """Analyze reference image."""

        image = open_image_from_bytes(image_bytes)

        detections = self._detector.detect(image)

        unique_labels = self._unique(
            [item.label for item in detections]
        )

        dominant_colors = [
            color.name
            for color in extract_dominant_colors(image, top_k=3)
        ]

        predicted_style = self._infer_reference_style(unique_labels)

        return ReferenceImageSummary(
            detected_categories=unique_labels[:8],
            dominant_colors=self._unique(dominant_colors)[:5],
            predicted_style_label=predicted_style,
        )

    def _score_template(
        self,
        template: RecommendationTemplate,
        occasion_bucket: str,
        weather_band: str,
        context: NormalizedUserContext,
        reference_labels: List[str],
    ) -> float:
        """Score template."""

        score = 0.0

        if occasion_bucket in template.occasions:
            score += 6.0

        if weather_band in template.weather_bands:
            score += 4.0

        if context.Gender == "female":
            if any(
                item in template.primary_items
                for item in {"dress", "jumpsuit"}
            ):
                score += 0.5

        if context.Gender == "male":
            if any(
                item in template.optional_items
                for item in {"tie", "belt"}
            ):
                score += 0.5

        if reference_labels:
            score += 0.4 * len(
                set(reference_labels).intersection(
                    template.primary_items
                )
            )

        return score

    def recommend(
        self,
        context: NormalizedUserContext,
        reference_image_bytes: bytes | None = None,
    ) -> RecommendOutfitResponse:
        """Generate recommendations."""

        logger.info("Starting recommendation engine")

        occasion_bucket = self._normalize_occasion_bucket(
            context.Occasion
        )

        weather_band = self._infer_weather_band(
            context.Weather,
            context.Temperature_celsius,
        )

        reference_summary = None
        reference_labels: List[str] = []
        reference_colors: List[str] = []

        if reference_image_bytes is not None:
            reference_summary = self._summarize_reference_image(
                reference_image_bytes
            )

            reference_labels = (
                reference_summary.detected_categories
            )

            reference_colors = (
                reference_summary.dominant_colors
            )

        scored_templates = []

        for template in self.TEMPLATES:
            template_score = self._score_template(
                template=template,
                occasion_bucket=occasion_bucket,
                weather_band=weather_band,
                context=context,
                reference_labels=reference_labels,
            )

            scored_templates.append(
                (template_score, template)
            )

        scored_templates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        top_templates = scored_templates[
            : self._settings.recommendation_count
        ]

        recommendations: List[OutfitRecommendation] = []

        for rank, (score, template) in enumerate(
            top_templates,
            start=1,
        ):
            primary_items = self._replace_avoided_items(
                list(template.primary_items),
                context.Avoid_items,
            )

            optional_items = self._replace_avoided_items(
                list(template.optional_items),
                context.Avoid_items,
            )

            style_details = self._replace_avoided_items(
                list(template.style_details),
                context.Avoid_items,
            )

            palette_direction = (
                self._unique(context.Color_preferences)
                if context.Color_preferences
                else self._unique(reference_colors)
                if reference_colors
                else list(template.palette_direction)
            )

            confidence = round(
                min(0.99, 0.45 + max(score, 0.0) / 16.0),
                4,
            )

            recommendations.append(
                OutfitRecommendation(
                    Rank=rank,
                    Title=template.title,
                    Style_label=template.style_label,
                    Confidence=confidence,
                    Primary_items=self._unique(primary_items),
                    Optional_items=self._unique(optional_items),
                    Style_details=self._unique(style_details),
                    Attribute_direction=self._build_attribute_direction(
                        template
                    ),
                    Palette_direction=self._unique(
                        palette_direction
                    ),
                    Reasoning=[
                        f"Matches the '{occasion_bucket}' occasion.",
                        f"Suitable for '{weather_band}' weather.",
                    ],
                )
            )

        deprioritized_items = self._unique(
            context.Avoid_items
        )

        notes = [
            "Recommendations are ontology-driven.",
            "Built using Fashionpedia labels and attributes.",
        ]

        return RecommendOutfitResponse(
            Context=context,
            Reference_image_summary=reference_summary,
            Recommendations=recommendations,
            Deprioritized_items=deprioritized_items,
            Notes=notes,
        )