from __future__ import annotations

"""
Pydantic schemas used by the public API.

The goal of this module is to keep the request and response contracts
explicit, versionable, and easy to discover inside editor tooling.
"""

# ============================================================================
# IMPORTS
# ============================================================================

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# STANDARDIZED ERROR RESPONSE
# ============================================================================

class ErrorResponse(BaseModel):
    """
    Standardized error payload returned for all non-2xx HTTP responses.
    """

    model_config = ConfigDict(extra="forbid")

    Status_code: int = Field(
        ...,
        description="HTTP status code (e.g. 400, 413, 500).",
    )

    Error: str = Field(
        ...,
        description="Short error type label.",
    )

    Detail: str = Field(
        ...,
        description="Human-readable explanation of the error.",
    )

    Request_id: Optional[str] = Field(
        default=None,
        description="Request tracking ID for log correlation.",
    )


# ============================================================================
# USER CONTEXT
# ============================================================================

class NormalizedUserContext(BaseModel):
    """
    Normalized user metadata extracted from multipart form fields.
    """

    model_config = ConfigDict(extra="forbid")

    User_id: Optional[str] = Field(
        default=None,
        description="Opaque user identifier.",
    )

    Gender: Optional[str] = Field(
        default=None,
        description="Normalized gender text.",
    )

    Occasion: Optional[str] = Field(
        default=None,
        description="Normalized occasion text.",
    )

    Weather: Optional[str] = Field(
        default=None,
        description="Normalized weather text.",
    )

    Temperature_celsius: Optional[float] = Field(
        default=None,
        description="Ambient temperature in Celsius.",
    )

    Dress_code: Optional[str] = Field(
        default=None,
        description="Normalized dress-code text.",
    )

    Style_preferences: List[str] = Field(
        default_factory=list,
        description="Parsed style preferences.",
    )

    Color_preferences: List[str] = Field(
        default_factory=list,
        description="Parsed color preferences.",
    )

    Avoid_items: List[str] = Field(
        default_factory=list,
        description="Items the user prefers to avoid.",
    )


# ============================================================================
# COLORS
# ============================================================================

class NamedColor(BaseModel):
    """
    Human-readable color information.
    """

    model_config = ConfigDict(extra="forbid")

    Name: str = Field(
        ...,
        description="Nearest human-readable color name.",
    )

    Rgb: Tuple[int, int, int] = Field(
        ...,
        description="RGB color tuple.",
    )

    Hex: str = Field(
        ...,
        description="Hexadecimal color string.",
    )

    Coverage: float = Field(
        ...,
        description="Approximate palette coverage from 0 to 1.",
    )


# ============================================================================
# FILE METADATA
# ============================================================================

class FileMetadata(BaseModel):
    """
    Metadata about the uploaded file.
    """

    model_config = ConfigDict(extra="forbid")

    File_name: str = Field(
        ...,
        description="Original uploaded file name.",
    )

    Content_type: str = Field(
        ...,
        description="Uploaded content type.",
    )

    File_size_bytes: int = Field(
        ...,
        description="Uploaded file size in bytes.",
    )

    Sha256: str = Field(
        ...,
        description="SHA-256 digest of the uploaded file.",
    )


# ============================================================================
# TECHNICAL IMAGE METADATA
# ============================================================================

class TechnicalMetadata(BaseModel):
    """
    Technical metadata extracted from the image.
    """

    model_config = ConfigDict(extra="forbid")

    Width: int = Field(
        ...,
        description="Image width in pixels.",
    )

    Height: int = Field(
        ...,
        description="Image height in pixels.",
    )

    Aspect_ratio: float = Field(
        ...,
        description="Width divided by height.",
    )

    Orientation: str = Field(
        ...,
        description="portrait, landscape, or square.",
    )

    Megapixels: float = Field(
        ...,
        description="Image size expressed in megapixels.",
    )

    Mode: str = Field(
        ...,
        description="Pillow image mode.",
    )

    Has_alpha: bool = Field(
        ...,
        description="Whether the image includes transparency.",
    )

    Is_animated: bool = Field(
        ...,
        description="Whether the image has multiple frames.",
    )

    Frame_count: int = Field(
        ...,
        description="Image frame count.",
    )

    Icc_profile_present: bool = Field(
        ...,
        description="Whether an ICC profile exists.",
    )

    Exif_present: bool = Field(
        ...,
        description="Whether EXIF data exists.",
    )

    Dpi: Optional[Tuple[int, int]] = Field(
        default=None,
        description="Image DPI tuple.",
    )

    Exif_summary: Dict[str, str] = Field(
        default_factory=dict,
        description="Safe subset of EXIF metadata.",
    )


# ============================================================================
# IMAGE QUALITY METADATA
# ============================================================================

class QualityMetadata(BaseModel):
    """
    Quality and aesthetic signals derived from the image.
    """

    model_config = ConfigDict(extra="forbid")

    Brightness_mean: float = Field(
        ...,
        description="Mean grayscale brightness.",
    )

    Contrast_stddev: float = Field(
        ...,
        description="Grayscale standard deviation.",
    )

    Entropy: float = Field(
        ...,
        description="Image entropy value.",
    )

    Sharpness_laplacian_variance: float = Field(
        ...,
        description="Laplacian variance used as a blur proxy.",
    )

    Edge_density: float = Field(
        ...,
        description="Fraction of pixels marked as edges.",
    )

    Dominant_colors: List[NamedColor] = Field(
        default_factory=list,
        description="Dominant colors for the whole image.",
    )

    Quality_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about darkness, blur, or low resolution.",
    )


# ============================================================================
# BOUNDING BOX
# ============================================================================

class BoundingBox(BaseModel):
    """
    Axis-aligned bounding box.
    """

    model_config = ConfigDict(extra="forbid")

    X_min: float = Field(
        ...,
        description="Left pixel coordinate.",
    )

    Y_min: float = Field(
        ...,
        description="Top pixel coordinate.",
    )

    X_max: float = Field(
        ...,
        description="Right pixel coordinate.",
    )

    Y_max: float = Field(
        ...,
        description="Bottom pixel coordinate.",
    )

    Width: float = Field(
        ...,
        description="Bounding-box width in pixels.",
    )

    Height: float = Field(
        ...,
        description="Bounding-box height in pixels.",
    )

    Area: float = Field(
        ...,
        description="Bounding-box area in square pixels.",
    )


# ============================================================================
# DETECTED ITEM
# ============================================================================

class DetectedItem(BaseModel):
    """
    Single Fashionpedia item detected in an image.
    """

    model_config = ConfigDict(extra="forbid")

    Category_id: int = Field(
        ...,
        description="Fashionpedia category identifier.",
    )

    Label: str = Field(
        ...,
        description="Fashionpedia category label.",
    )

    Supercategory: str = Field(
        ...,
        description="Fashionpedia supercategory.",
    )

    Confidence: float = Field(
        ...,
        description="Detector confidence.",
    )

    Bounding_box: BoundingBox = Field(
        ...,
        description="Detected bounding box.",
    )

    Crop_palette: List[NamedColor] = Field(
        default_factory=list,
        description="Dominant colors extracted from the detected crop.",
    )


# ============================================================================
# OUTFIT BREAKDOWN
# ============================================================================

class OutfitBreakdown(BaseModel):
    """
    Grouped Fashionpedia detections for easier client consumption.
    """

    model_config = ConfigDict(extra="forbid")

    Upper_body: List[str] = Field(default_factory=list)
    Lower_body: List[str] = Field(default_factory=list)
    One_piece: List[str] = Field(default_factory=list)
    Outerwear: List[str] = Field(default_factory=list)
    Footwear: List[str] = Field(default_factory=list)
    Accessories: List[str] = Field(default_factory=list)
    Garment_parts: List[str] = Field(default_factory=list)
    Closures: List[str] = Field(default_factory=list)
    Decorations: List[str] = Field(default_factory=list)


# ============================================================================
# CONTEXT FIT PREDICTION
# ============================================================================

class ContextFitPrediction(BaseModel):
    """
    Context-aware interpretation of the uploaded outfit.
    """

    model_config = ConfigDict(extra="forbid")

    Predicted_style_label: str = Field(
        ...,
        description="Predicted style label.",
    )

    Best_matching_occasion: Optional[str] = Field(
        default=None,
        description="Best matching occasion inferred from the image.",
    )

    Weather_alignment: Optional[str] = Field(
        default=None,
        description="good, moderate, poor, or unknown.",
    )

    Occasion_alignment: Optional[str] = Field(
        default=None,
        description="good, moderate, poor, or unknown.",
    )

    Confidence: float = Field(
        ...,
        description="Confidence score between 0 and 1.",
    )

    Reasoning: List[str] = Field(
        default_factory=list,
        description="Prediction rationale.",
    )


# ============================================================================
# ANALYZE IMAGE RESPONSE
# ============================================================================

class AnalyzeImageResponse(BaseModel):
    """
    Response payload for `/images/analyze`.
    """

    model_config = ConfigDict(extra="forbid")

    Context: NormalizedUserContext = Field(
        ...,
        description="Normalized user metadata.",
    )

    File_metadata: FileMetadata = Field(
        ...,
        description="File-level metadata.",
    )

    Technical_metadata: TechnicalMetadata = Field(
        ...,
        description="Technical image metadata.",
    )

    Quality_metadata: QualityMetadata = Field(
        ...,
        description="Quality and palette signals.",
    )

    Detector_backend: str = Field(
        ...,
        description="Logical detector backend name.",
    )

    Detector_model_name: str = Field(
        ...,
        description="Underlying model name.",
    )

    Fashionpedia_detections: List[DetectedItem] = Field(
        default_factory=list,
        description="Detected Fashionpedia items.",
    )

    Detected_outfit_summary: OutfitBreakdown = Field(
        ...,
        description="Grouped outfit summary.",
    )

    Counts_by_label: Dict[str, int] = Field(
        default_factory=dict,
    )

    Counts_by_supercategory: Dict[str, int] = Field(
        default_factory=dict,
    )

    Outfit_prediction: ContextFitPrediction = Field(
        ...,
        description="Context fit prediction.",
    )

    Notes: List[str] = Field(
        default_factory=list,
        description="Important caveats.",
    )


# ============================================================================
# ATTRIBUTE DIRECTION
# ============================================================================

class AttributeDirection(BaseModel):
    """
    Suggested Fashionpedia attribute direction.
    """

    model_config = ConfigDict(extra="forbid")

    Supercategory: str = Field(
        ...,
        description="Fashionpedia attribute supercategory.",
    )

    Suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested attributes.",
    )


# ============================================================================
# REFERENCE IMAGE SUMMARY
# ============================================================================

class ReferenceImageSummary(BaseModel):
    """
    Optional summary derived from a reference image.
    """

    model_config = ConfigDict(extra="forbid")

    Detected_categories: List[str] = Field(default_factory=list)

    Dominant_colors: List[str] = Field(default_factory=list)

    Predicted_style_label: Optional[str] = Field(default=None)


# ============================================================================
# OUTFIT RECOMMENDATION
# ============================================================================

class OutfitRecommendation(BaseModel):
    """
    One ranked outfit recommendation.
    """

    model_config = ConfigDict(extra="forbid")

    Rank: int = Field(
        ...,
        description="Ranking position starting from 1.",
    )

    Title: str = Field(
        ...,
        description="Human-readable recommendation title.",
    )

    Style_label: str = Field(
        ...,
        description="Compact style label.",
    )

    Confidence: float = Field(
        ...,
        description="Confidence score between 0 and 1.",
    )

    Primary_items: List[str] = Field(default_factory=list)

    Optional_items: List[str] = Field(default_factory=list)

    Style_details: List[str] = Field(default_factory=list)

    Attribute_direction: List[AttributeDirection] = Field(
        default_factory=list,
    )

    Palette_direction: List[str] = Field(default_factory=list)

    Reasoning: List[str] = Field(default_factory=list)


# ============================================================================
# RECOMMEND OUTFIT RESPONSE
# ============================================================================

class RecommendOutfitResponse(BaseModel):
    """
    Response payload for `/outfits/recommend`.
    """

    model_config = ConfigDict(extra="forbid")

    Context: NormalizedUserContext = Field(...)

    Reference_image_summary: Optional[ReferenceImageSummary] = Field(
        default=None,
    )

    Recommendations: List[OutfitRecommendation] = Field(
        default_factory=list,
    )

    Deprioritized_items: List[str] = Field(
        default_factory=list,
    )

    Notes: List[str] = Field(
        default_factory=list,
    )