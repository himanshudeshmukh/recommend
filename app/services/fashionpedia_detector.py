from __future__ import annotations

"""Fashionpedia detector backend.

The default backend is a lightweight Hugging Face object detector fine-tuned on
Fashionpedia category labels. The module is intentionally designed with lazy
imports so the rest of the application can still start even before heavy ML
packages are installed.
"""

# Import threading so model loading is safe under concurrent requests.
import threading

# Import logging for operational visibility.
import logging

# Import typing helpers for clearer signatures.
from typing import Any

# Import PIL so the detector can accept Pillow images.
from PIL import Image

# Import configuration and schema objects used by the detector.
from app.core.config import Settings
from app.models.schemas import BoundingBox, DetectedItem
from app.services.fashionpedia_catalog import FashionpediaCatalog
from app.services.vision_utils import extract_dominant_colors

# Create a module-level logger for detector events.
logger = logging.getLogger(__name__)


# Define the detector wrapper used by the API service.
class FashionpediaDetector:
    """Lazy-loading Fashionpedia detector built on top of Hugging Face models."""

    def __init__(
        self,
        settings: Settings,
        catalog: FashionpediaCatalog,
    ) -> None:
        """Store configuration and ontology dependencies."""

        # Store the immutable application settings.
        self._settings = settings

        # Store the Fashionpedia ontology catalog.
        self._catalog = catalog

        # Create a lock so model loading happens only once.
        self._load_lock = threading.Lock()

        # Initialize the processor slot before lazy loading.
        self._processor: Any | None = None

        # Initialize the model slot before lazy loading.
        self._model: Any | None = None

        # Initialize the device slot before lazy loading.
        self._device: Any | None = None

        # Background loading helpers.
        self._loaded_event = threading.Event()
        self._loading_thread: threading.Thread | None = None
        self._load_error: Exception | None = None

        logger.info(
            "FashionpediaDetector created — model: '%s', device preference: '%s'.",
            settings.fashionpedia_model_name,
            settings.model_device,
        )

    @property
    def backend_name(self) -> str:
        """Return a stable logical backend name."""

        return "huggingface-yolos-fashionpedia"

    @property
    def model_name(self) -> str:
        """Return the configured model identifier."""

        return self._settings.fashionpedia_model_name

    def _resolve_device(self, torch_module: Any) -> Any:
        """Resolve the actual torch device for model execution."""

        requested_device = self._settings.model_device.strip().lower()

        logger.info(
            "Resolving compute device — requested: '%s'.",
            requested_device,
        )

        # Respect explicit device override.
        if requested_device in {"cpu", "cuda"}:
            if (
                requested_device == "cuda"
                and not torch_module.cuda.is_available()
            ):
                logger.warning(
                    "CUDA requested but unavailable — falling back to CPU."
                )
                return torch_module.device("cpu")

            logger.info(
                "Using explicitly requested device: '%s'.",
                requested_device,
            )

            return torch_module.device(requested_device)

        # Auto-detect best available device.
        chosen = (
            "cuda"
            if torch_module.cuda.is_available()
            else "cpu"
        )

        logger.info(
            "Auto-detecting device — CUDA available: %s → using '%s'.",
            torch_module.cuda.is_available(),
            chosen,
        )

        return torch_module.device(chosen)

    def _load_model(self) -> None:
        """Load the detector model and processor into memory."""

        with self._load_lock:
            if self._processor is not None and self._model is not None:
                logger.debug("Model already loaded — skipping reload.")
                self._loaded_event.set()
                return

            self._load_error = None
            self._loaded_event.clear()

            logger.info(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        logger.info(
            "🤖 Loading the AI fashion detection model..."
        )
        logger.info(
            "Model name: '%s'",
            self._settings.fashionpedia_model_name,
        )
        logger.info(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        try:
            # Lazy imports.
            logger.info(
                "Importing PyTorch (this may take a moment)..."
            )
            import torch

            logger.info(
                "Importing Transformers library..."
            )

            from transformers import (
                AutoImageProcessor,
                AutoModelForObjectDetection,
            )

            logger.info(
                "✓ PyTorch and Transformers imported successfully."
            )

        except ImportError as exc:
            logger.error(
                "Failed to import torch/transformers."
            )

            self._load_error = RuntimeError(
                "The detector backend requires `transformers` and `torch`."
            )
            self._loaded_event.set()
            return

        import os
        import time

        # Set environment variable to show download progress.
        os.environ["HF_HUB_VERBOSE"] = "1"

        logger.info(
            "Step 1/4: Downloading and loading image processor..."
        )
        logger.info(
            "Note: First download may take several minutes (~100-300 MB)."
        )

        start_time = time.time()

        try:
            self._processor = (
                AutoImageProcessor.from_pretrained(
                    self._settings.fashionpedia_model_name,
                )
            )

            elapsed = time.time() - start_time
            logger.info(
                "✓ Image processor loaded successfully (%.1f seconds).",
                elapsed,
            )

        except Exception as exc:
            logger.exception(
                "Failed to load image processor from Hugging Face."
            )

            msg = str(exc) or ""

            if "Torchvision" in msg or "torchvision" in msg:
                self._load_error = RuntimeError(
                    "AutoImageProcessor requires the `torchvision` package.\n"
                    "Please install a compatible `torchvision` for your PyTorch build (see: https://pytorch.org/get-started/locally/)."
                )
            else:
                self._load_error = RuntimeError(
                    "Could not download or load the image processor."
                )
            self._loaded_event.set()
            return

        logger.info(
            "Step 2/4: Downloading and loading object detection model..."
        )
        logger.info(
            "Note: This is the largest component (~300-500 MB)."
        )

        start_time = time.time()

        try:
            self._model = (
                AutoModelForObjectDetection.from_pretrained(
                    self._settings.fashionpedia_model_name,
                )
            )

            elapsed = time.time() - start_time
            logger.info(
                "✓ Detection model loaded successfully (%.1f seconds).",
                elapsed,
            )

        except Exception as exc:
            logger.exception(
                "Failed to load detection model from Hugging Face."
            )
            self._load_error = RuntimeError(
                "Could not download or load the detection model."
            )
            self._loaded_event.set()
            return

        logger.info(
            "Step 3/4: Selecting compute device..."
        )

        self._device = self._resolve_device(torch)

        logger.info(
            "Step 4/4: Moving model to device..."
        )

        self._model.to(self._device)
        self._model.eval()

        logger.info(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        logger.info(
            "✅ Fashion detection model ready on device: '%s'.",
            self._device,
        )

        logger.info(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        self._loaded_event.set()

    def _ensure_loaded(self) -> None:
        """Load the detector model and processor exactly once."""

        if self._processor is not None and self._model is not None:
            logger.debug("Model already loaded — skipping reload.")
            return

        if self._loading_thread is not None and self._loading_thread.is_alive():
            logger.info(
                "Waiting for background model warmup to complete..."
            )
            self._loaded_event.wait()

        if self._load_error is not None:
            raise self._load_error

        if self._processor is None or self._model is None:
            self._load_model()

        if self._load_error is not None:
            raise self._load_error

    def warmup(self, background: bool = True) -> None:
        """Warm the model so the first live request is faster."""

        if self._processor is not None and self._model is not None:
            logger.info("🔥 Fashionpedia model is already warmed.")
            return

        if background:
            if self._loading_thread is not None and self._loading_thread.is_alive():
                logger.info(
                    "🔥 Background warmup already in progress — continuing to load..."
                )
                return

            self._load_error = None
            self._loaded_event.clear()

            logger.info(
                "🔥 Starting background fashion detector warmup..."
            )
            self._loading_thread = threading.Thread(
                target=self._load_model,
                name="FashionpediaWarmupThread",
                daemon=True,
            )
            self._loading_thread.start()
            return

        logger.info(
            "🔥 Warming up the fashion detector in the foreground..."
        )

        self._load_model()

        if self._load_error is not None:
            raise self._load_error

        logger.info(
            "🔥 Warmup complete."
        )

    def detect(
        self,
        image: Image.Image,
        threshold: float | None = None,
    ) -> list[DetectedItem]:
        """Run Fashionpedia detection on a Pillow image."""

        logger.info(
            "🔍 Starting fashion detection..."
        )

        self._ensure_loaded()

        import torch

        effective_threshold = (
            threshold
            if threshold is not None
            else self._settings.detection_threshold
        )

        logger.info(
            "Confidence threshold set to %.2f.",
            effective_threshold,
        )

        rgb_image = image.convert("RGB")

        logger.info(
            "Image converted to RGB. Size: %dx%d",
            rgb_image.width,
            rgb_image.height,
        )

        logger.info(
            "Preparing image for the AI model..."
        )

        inputs = self._processor(
            images=rgb_image,
            return_tensors="pt",
        )

        inputs = {
            key: value.to(self._device)
            for key, value in inputs.items()
        }

        logger.info(
            "Running AI inference..."
        )

        with torch.inference_mode():
            outputs = self._model(**inputs)

        logger.info(
            "Inference completed."
        )

        target_sizes = torch.tensor(
            [(rgb_image.height, rgb_image.width)],
            device=self._device,
        )

        processed = (
            self._processor.post_process_object_detection(
                outputs,
                threshold=effective_threshold,
                target_sizes=target_sizes,
            )[0]
        )

        num_raw = len(processed["scores"])

        logger.info(
            "Model produced %d detections.",
            num_raw,
        )

        detections: list[DetectedItem] = []

        for idx, (
            score_tensor,
            label_tensor,
            box_tensor,
        ) in enumerate(
            zip(
                processed["scores"],
                processed["labels"],
                processed["boxes"],
            )
        ):
            category_id = int(label_tensor.item())
            confidence = float(score_tensor.item())

            try:
                category = self._catalog.get_category(
                    category_id
                )

                label_name = category.Name
                supercategory = category.Supercategory

            except KeyError:
                fallback_label = getattr(
                    self._model.config,
                    "id2label",
                    {},
                ).get(
                    category_id,
                    f"label_{category_id}",
                )

                label_name = fallback_label
                supercategory = "unknown"

                logger.warning(
                    "Category ID %d missing in catalog.",
                    category_id,
                )

            x_min, y_min, x_max, y_max = [
                float(value)
                for value in box_tensor.tolist()
            ]

            x_min = max(
                0.0,
                min(x_min, float(rgb_image.width)),
            )

            y_min = max(
                0.0,
                min(y_min, float(rgb_image.height)),
            )

            x_max = max(
                0.0,
                min(x_max, float(rgb_image.width)),
            )

            y_max = max(
                0.0,
                min(y_max, float(rgb_image.height)),
            )

            box_width = max(0.0, x_max - x_min)
            box_height = max(0.0, y_max - y_min)

            logger.info(
                "Detection %d → '%s' (%.1f%%)",
                idx + 1,
                label_name,
                confidence * 100,
            )

            crop = rgb_image.crop(
                (
                    int(x_min),
                    int(y_min),
                    int(x_max),
                    int(y_max),
                )
            )

            crop_palette = extract_dominant_colors(
                crop,
                top_k=min(
                    3,
                    self._settings.dominant_color_count,
                ),
            )

            detections.append(
                DetectedItem(
                    Category_id=category_id,
                    Label=label_name,
                    Supercategory=supercategory,
                    Confidence=round(confidence, 4),
                    Bounding_box=BoundingBox(
                        X_min=round(x_min, 2),
                        Y_min=round(y_min, 2),
                        X_max=round(x_max, 2),
                        Y_max=round(y_max, 2),
                        Width=round(box_width, 2),
                        Height=round(box_height, 2),
                        Area=round(
                            box_width * box_height,
                            2,
                        ),
                    ),
                    Crop_palette=crop_palette,
                )
            )

        logger.info(
            "🔍 Fashion detection complete — returning %d item(s).",
            len(detections),
        )

        return detections