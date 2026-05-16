from __future__ import annotations

"""Image utility helpers shared by the detector and analysis service."""

# Import hashlib so we can fingerprint uploads with SHA-256.
import hashlib

# Import in-memory byte-stream helpers for safe image loading.
import io

# Import the standard logging module so we can write readable progress messages.
import logging

# Import EXIF tag names for a readable metadata summary.
from PIL import ExifTags

# Import the Pillow Image class used throughout the service.
from PIL import Image

# Import the Pillow exception raised when an invalid image is uploaded.
from PIL import UnidentifiedImageError

# Import NumPy for efficient numerical work on image arrays.
import numpy as np

# Import OpenCV for image-quality heuristics like edge density and blur estimation.
import cv2

# Import response models so these helpers can return strongly typed structures.
from app.models.schemas import NamedColor, QualityMetadata, TechnicalMetadata


# Create a logger dedicated to this module so messages are easy to filter.
logger = logging.getLogger(__name__)


# Define a small, practical color dictionary used to name extracted palette colors.
COLOR_NAME_TABLE = [
    ("black", (0, 0, 0)),
    ("white", (255, 255, 255)),
    ("gray", (128, 128, 128)),
    ("silver", (192, 192, 192)),
    ("red", (220, 20, 60)),
    ("orange", (255, 140, 0)),
    ("yellow", (255, 215, 0)),
    ("green", (34, 139, 34)),
    ("olive", (107, 142, 35)),
    ("teal", (0, 128, 128)),
    ("blue", (30, 144, 255)),
    ("navy", (0, 0, 128)),
    ("purple", (128, 0, 128)),
    ("pink", (255, 105, 180)),
    ("brown", (139, 69, 19)),
    ("beige", (245, 245, 220)),
    ("cream", (255, 253, 208)),
    ("burgundy", (128, 0, 32)),
    ("gold", (212, 175, 55)),
]


# Compute the SHA-256 digest for the uploaded file so callers can track duplicates.
def compute_sha256(file_bytes: bytes) -> str:
    """Return the SHA-256 digest for a byte sequence."""

    logger.info(
        "Starting to compute a unique fingerprint (SHA-256 hash) for the uploaded file (%d bytes).",
        len(file_bytes),
    )

    # Build the digest and return it as a hexadecimal string.
    digest = hashlib.sha256(file_bytes).hexdigest()

    logger.info(
        "Fingerprint computed successfully. Hash: %s (first 12 chars shown: %s...).",
        digest,
        digest[:12],
    )

    return digest


# Load an image from raw bytes and force materialization so the byte stream can be released.
def open_image_from_bytes(file_bytes: bytes) -> Image.Image:
    """Safely open an image from raw bytes.

    Raises:
        ValueError: When the bytes do not represent a valid image.
    """

    logger.info(
        "Attempting to open the uploaded file as an image (%d bytes received).",
        len(file_bytes),
    )

    try:
        # Wrap the raw bytes in a file-like object that Pillow can read from.
        buffer = io.BytesIO(file_bytes)

        # Open the image without assuming any particular format.
        image = Image.open(buffer)

        logger.info(
            "Image file recognized. Format: %s, Size: %dx%d, Color mode: %s.",
            image.format,
            image.size[0],
            image.size[1],
            image.mode,
        )

        # Fully load the image into memory so it is detached from the byte stream.
        image.load()

        logger.info("Image fully loaded into memory and ready for processing.")

        # Return the loaded image object.
        return image

    except UnidentifiedImageError as exc:
        logger.error(
            "The uploaded file could not be recognized as a valid image. "
            "It may be corrupted or not an image file at all."
        )

        # Convert Pillow's low-level error into a clean domain-specific exception.
        raise ValueError("Uploaded file is not a valid image.") from exc


# Convert an RGB triplet into a CSS-style hexadecimal color string.
def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert an RGB tuple into hex notation."""

    # Format the integer channel values into a `#RRGGBB` string.
    return "#{:02x}{:02x}{:02x}".format(*rgb)


# Find the nearest human-readable color name using Euclidean RGB distance.
def nearest_color_name(rgb: tuple[int, int, int]) -> str:
    """Map an RGB color to the nearest predefined color name."""

    logger.debug(
        "Looking up the closest color name for RGB(%d, %d, %d).",
        rgb[0],
        rgb[1],
        rgb[2],
    )

    # Initialize the best distance with positive infinity.
    best_distance = float("inf")

    # Initialize the best color name with a neutral default.
    best_name = "unknown"

    # Compare the input color against every named color in the table.
    for color_name, reference_rgb in COLOR_NAME_TABLE:
        # Compute squared Euclidean distance between the two RGB triplets.
        distance = sum(
            (input_channel - reference_channel) ** 2
            for input_channel, reference_channel in zip(rgb, reference_rgb)
        )

        # Update the winner when a closer named color is found.
        if distance < best_distance:
            best_distance = distance
            best_name = color_name

    logger.debug(
        "Closest color name for RGB(%d, %d, %d) is '%s'.",
        rgb[0],
        rgb[1],
        rgb[2],
        best_name,
    )

    # Return the nearest human-readable color name.
    return best_name


# Convert image dimensions into a friendly orientation label.
def orientation_from_dimensions(width: int, height: int) -> str:
    """Return portrait, landscape, or square based on dimensions."""

    # Mark the image as portrait when height is greater than width.
    if height > width:
        return "portrait"

    # Mark the image as landscape when width is greater than height.
    if width > height:
        return "landscape"

    # Fall back to `square` when both dimensions are identical.
    return "square"


# Normalize arbitrary EXIF values into safe short strings for API responses.
def _sanitize_exif_value(value: object) -> str:
    """Convert arbitrary EXIF values into compact strings."""

    # Convert bytes into a shortened human-readable representation.
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"

    # Convert tuples into a comma-separated string for readability.
    if isinstance(value, tuple):
        return ", ".join(str(item) for item in value[:8])

    # Convert all other values using the built-in string conversion.
    return str(value)


# Extract a small EXIF summary instead of sending raw metadata back to the caller.
def extract_exif_summary(
    image: Image.Image,
    max_items: int = 20,
) -> dict[str, str]:
    """Extract a safe subset of EXIF metadata."""

    logger.info(
        "Checking the image for EXIF metadata (camera info, date taken, etc.)."
    )

    # Build an empty summary in case the image has no EXIF data.
    summary: dict[str, str] = {}

    try:
        # Ask Pillow for the parsed EXIF dictionary.
        exif = image.getexif()

    except Exception:
        logger.warning(
            "Could not read EXIF data from this image — it may not contain any camera metadata."
        )

        # Return an empty summary when EXIF extraction fails.
        return summary

    # Stop early when the image has no EXIF data.
    if not exif:
        logger.info("No EXIF metadata found in this image.")
        return summary

    # Iterate over the EXIF entries and keep only a small safe subset.
    for index, (tag_id, raw_value) in enumerate(exif.items()):
        # Respect the maximum number of items to avoid noisy payloads.
        if index >= max_items:
            break

        # Translate numeric EXIF tags into human-readable names.
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))

        # Store the sanitized value in the summary dictionary.
        summary[tag_name] = _sanitize_exif_value(raw_value)

    logger.info(
        "Extracted %d EXIF metadata entries (e.g. camera model, date, settings).",
        len(summary),
    )

    # Return the final EXIF summary.
    return summary


# Extract a small color palette from an image region using Pillow quantization.
def extract_dominant_colors(
    image: Image.Image,
    top_k: int = 5,
) -> list[NamedColor]:
    """Extract dominant colors from an image as named palette entries."""

    logger.info(
        "Starting dominant-color extraction — finding the top %d most common colors in the image.",
        top_k,
    )

    # Return an empty palette when the image area is invalid.
    if image.width <= 0 or image.height <= 0:
        logger.warning(
            "Image has invalid dimensions (%dx%d). Returning an empty color palette.",
            image.width,
            image.height,
        )
        return []

    # Convert the image to RGB so color extraction behaves consistently.
    working_image = image.convert("RGB")

    logger.info(
        "Converted image to standard RGB color space for consistent color analysis."
    )

    # Downscale the image to keep palette extraction fast and deterministic.
    working_image.thumbnail((200, 200))

    logger.info(
        "Resized image to a small thumbnail (%dx%d) to speed up color analysis.",
        working_image.width,
        working_image.height,
    )

    # Quantize the image into a small fixed palette.
    quantized = working_image.quantize(
        colors=max(top_k, 1),
        method=Image.MEDIANCUT,
    )

    logger.info(
        "Reduced the image to only %d distinct colors using median-cut quantization.",
        max(top_k, 1),
    )

    # Convert the quantized image back to RGB for simpler processing.
    quantized_rgb = quantized.convert("RGB")

    # Ask Pillow for the colors present in the quantized image.
    color_counts = quantized_rgb.getcolors(
        maxcolors=working_image.width * working_image.height
    )

    # Guard against the unlikely case where Pillow returns no colors.
    if not color_counts:
        logger.warning(
            "No colors could be extracted from the image — returning an empty palette."
        )
        return []

    # Compute the total number of sampled pixels so coverage can be normalized.
    total_pixels = sum(count for count, _ in color_counts)

    # Sort the palette by descending frequency and keep only the requested top colors.
    sorted_colors = sorted(
        color_counts,
        key=lambda item: item[0],
        reverse=True,
    )[:top_k]

    # Build the typed list expected by the public API contract.
    named_colors: list[NamedColor] = []

    # Convert each raw RGB color into a typed NamedColor payload.
    for count, rgb in sorted_colors:
        # Cast the palette values to plain Python integers.
        rgb_tuple = (int(rgb[0]), int(rgb[1]), int(rgb[2]))

        color_name = nearest_color_name(rgb_tuple)
        coverage = round(count / max(total_pixels, 1), 4)

        logger.info(
            "  • Color found: '%s' (RGB %s, hex %s) — covers %.1f%% of the image.",
            color_name,
            rgb_tuple,
            rgb_to_hex(rgb_tuple),
            coverage * 100,
        )

        # Append the normalized color entry to the result list.
        named_colors.append(
            NamedColor(
                name=color_name,
                rgb=rgb_tuple,
                hex=rgb_to_hex(rgb_tuple),
                coverage=coverage,
            )
        )

    logger.info(
        "Dominant-color extraction complete. Found %d colors.",
        len(named_colors),
    )

    # Return the final dominant-color list.
    return named_colors


# Build the technical metadata block used by the first API.
def build_technical_metadata(image: Image.Image) -> TechnicalMetadata:
    """Create the TechnicalMetadata response object."""

    logger.info(
        "=== Building technical metadata (dimensions, format info, EXIF) ==="
    )

    # Read the image dimensions once so downstream calculations stay simple.
    width, height = image.size

    logger.info(
        "Image dimensions: %d pixels wide × %d pixels tall.",
        width,
        height,
    )

    # Compute the image DPI tuple when available.
    raw_dpi = image.info.get("dpi")

    # Normalize the DPI value into a pair of integers when possible.
    dpi_value = None

    if isinstance(raw_dpi, tuple) and len(raw_dpi) >= 2:
        dpi_value = (int(raw_dpi[0]), int(raw_dpi[1]))

        logger.info(
            "Image DPI (dots per inch / print resolution): %s.",
            dpi_value,
        )

    else:
        logger.info(
            "No DPI information found — the image does not specify a print resolution."
        )

    # Read animation metadata if the image format supports multiple frames.
    frame_count = int(getattr(image, "n_frames", 1))

    if frame_count > 1:
        logger.info(
            "Image is animated and contains %d frames (e.g. a GIF).",
            frame_count,
        )

    else:
        logger.info("Image is a single still frame (not animated).")

    # Determine whether the image carries transparency information.
    has_alpha = "A" in image.mode or image.mode in {"LA", "PA"}

    logger.info(
        "Transparency (alpha channel): %s.",
        "Yes — image has transparent areas"
        if has_alpha
        else "No — image is fully opaque",
    )

    # Convert image dimensions into a friendly orientation label.
    orientation = orientation_from_dimensions(width, height)

    # Compute the total number of megapixels for the image.
    megapixels = round((width * height) / 1_000_000, 4)

    logger.info(
        "Orientation: %s. Total resolution: %s megapixels.",
        orientation,
        megapixels,
    )

    # Extract the EXIF summary once so we avoid duplicate work.
    exif_summary = extract_exif_summary(image)

    logger.info("Technical metadata block assembled successfully.")

    # Build and return the strongly typed metadata payload.
    return TechnicalMetadata(
        width=width,
        height=height,
        aspect_ratio=round(width / max(height, 1), 4),
        orientation=orientation,
        megapixels=megapixels,
        mode=image.mode,
        has_alpha=has_alpha,
        is_animated=frame_count > 1,
        frame_count=frame_count,
        icc_profile_present="icc_profile" in image.info,
        exif_present=bool(exif_summary),
        dpi=dpi_value,
        exif_summary=exif_summary,
    )


# Build the quality-metadata block used by the first API.
def build_quality_metadata(
    image: Image.Image,
    top_k: int = 5,
) -> QualityMetadata:
    """Create the QualityMetadata response object."""

    logger.info(
        "=== Building quality metadata (brightness, sharpness, contrast, colors) ==="
    )

    # Convert the image to RGB so the NumPy array has a predictable shape.
    rgb_image = image.convert("RGB")

    # Convert the image into a NumPy array for vectorized processing.
    rgb_array = np.array(rgb_image)

    logger.info(
        "Converted image to a numerical array for quality analysis."
    )

    # Convert the RGB image into grayscale for quality heuristics.
    gray_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)

    logger.info(
        "Converted image to grayscale to measure brightness, contrast, and sharpness."
    )

    # Compute the mean grayscale brightness.
    brightness_mean = float(gray_array.mean())

    logger.info(
        "Average brightness: %.2f out of 255 (0 = pitch black, 255 = pure white). %s",
        brightness_mean,
        "The image looks dark."
        if brightness_mean < 45
        else "The image looks very bright."
        if brightness_mean > 210
        else "Brightness is in a normal range.",
    )

    # Compute the grayscale standard deviation as a contrast proxy.
    contrast_stddev = float(gray_array.std())

    logger.info(
        "Contrast (standard deviation): %.2f. %s",
        contrast_stddev,
        "Low contrast — the image looks flat/washed out."
        if contrast_stddev < 20
        else "Good contrast — details should be distinguishable.",
    )

    # Compute entropy using Pillow's built-in helper on the grayscale image.
    entropy_value = float(Image.fromarray(gray_array).entropy())

    logger.info(
        "Entropy (visual complexity): %.2f. Higher values mean more detail and texture in the image.",
        entropy_value,
    )

    # Compute Laplacian variance as a proxy for image sharpness.
    laplacian_variance = float(
        cv2.Laplacian(gray_array, cv2.CV_64F).var()
    )

    logger.info(
        "Sharpness (Laplacian variance): %.2f. %s",
        laplacian_variance,
        "The image may be blurry."
        if laplacian_variance < 60
        else "The image appears sharp and in focus.",
    )

    # Extract Canny edges so we can estimate scene complexity.
    edges = cv2.Canny(gray_array, 100, 200)

    # Compute the fraction of pixels classified as edges.
    edge_density = float(
        np.count_nonzero(edges) / max(edges.size, 1)
    )

    logger.info(
        "Edge density: %.4f (%.1f%% of pixels are edges). More edges usually mean a more complex scene.",
        edge_density,
        edge_density * 100,
    )

    # Extract dominant colors from the full image.
    dominant_colors = extract_dominant_colors(
        rgb_image,
        top_k=top_k,
    )

    # Build a list of warnings that may explain poor detector behavior.
    quality_warnings: list[str] = []

    # Add a warning when the image is too dark.
    if brightness_mean < 45:
        warning = "Image appears dark; model accuracy may drop."
        quality_warnings.append(warning)

        logger.warning("⚠️  Quality warning: %s", warning)

    # Add a warning when the image is too blurry.
    if laplacian_variance < 60:
        warning = (
            "Image may be blurry; fine garment details can be missed."
        )
        quality_warnings.append(warning)

        logger.warning("⚠️  Quality warning: %s", warning)

    # Add a warning when the image resolution is small.
    if image.width < 320 or image.height < 320:
        warning = (
            "Image resolution is low; small fashion items may be missed."
        )
        quality_warnings.append(warning)

        logger.warning("⚠️  Quality warning: %s", warning)

    # Add a warning when the image has weak contrast.
    if contrast_stddev < 20:
        warning = (
            "Image contrast is low; item boundaries may be less clear."
        )
        quality_warnings.append(warning)

        logger.warning("⚠️  Quality warning: %s", warning)

    if not quality_warnings:
        logger.info(
            "✅ No quality warnings — the image looks good for fashion detection."
        )

    else:
        logger.info(
            "Total quality warnings raised: %d.",
            len(quality_warnings),
        )

    logger.info("Quality metadata block assembled successfully.")

    # Return the typed quality payload.
    return QualityMetadata(
        brightness_mean=round(brightness_mean, 4),
        contrast_stddev=round(contrast_stddev, 4),
        entropy=round(entropy_value, 4),
        sharpness_laplacian_variance=round(
            laplacian_variance,
            4,
        ),
        edge_density=round(edge_density, 4),
        dominant_colors=dominant_colors,
        quality_warnings=quality_warnings,
    )