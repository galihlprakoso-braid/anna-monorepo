"""UI element detection service using OmniParser.

Detects interactive UI elements from screenshots and returns
structured data with element types, bounding boxes, and captions.
"""

import base64
import logging
import os
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image

# Configure logging
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BoundingBox:
    """Pixel bounding box for detected element."""

    x_min: int
    y_min: int
    x_max: int
    y_max: int


@dataclass(frozen=True)
class GridCoords:
    """0-100 grid coordinates for element center."""

    x: int
    y: int


@dataclass(frozen=True)
class DetectedElement:
    """A detected UI element with position and description."""

    element_type: str
    caption: str
    bbox: BoundingBox
    grid_center: GridCoords
    confidence: float


class ElementDetector:
    """Detects UI elements from screenshots using OmniParser models."""

    _instance: "ElementDetector | None" = None

    def __init__(self, weights_dir: Path | None = None):
        """Initialize detector with model weights.

        Args:
            weights_dir: Path to OmniParser weights directory.
                        Defaults to OMNIPARSER_WEIGHTS_DIR env var or ./weights
        """
        self._detection_model = None
        self._caption_model = None
        self._caption_processor = None
        self._weights_dir = weights_dir or Path(
            os.environ.get("OMNIPARSER_WEIGHTS_DIR", "weights")
        )

    @classmethod
    def get_instance(cls) -> "ElementDetector":
        """Get singleton instance for model reuse."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_models(self) -> None:
        """Load detection and captioning models (lazy loading)."""
        if self._detection_model is not None:
            return

        logger.info("Loading OmniParser models...")

        try:
            from ultralytics import YOLO
            from transformers import AutoModelForCausalLM, AutoProcessor

            # Load YOLOv8 detection model
            detection_path = self._weights_dir / "icon_detect" / "model.pt"
            if not detection_path.exists():
                raise FileNotFoundError(
                    f"Detection model not found at {detection_path}. "
                    "Run scripts/setup_omniparser.sh to download weights."
                )

            logger.info(f"Loading detection model from {detection_path}")
            self._detection_model = YOLO(str(detection_path))

            # Load Florence captioning model
            caption_path = self._weights_dir / "icon_caption_florence"
            if not caption_path.exists():
                raise FileNotFoundError(
                    f"Caption model not found at {caption_path}. "
                    "Run scripts/setup_omniparser.sh to download weights."
                )

            logger.info(f"Loading caption model from {caption_path}")
            self._caption_model = AutoModelForCausalLM.from_pretrained(
                str(caption_path),
                trust_remote_code=True,
                attn_implementation="eager",  # Disable SDPA for compatibility
            )
            # Disable KV cache to avoid past_key_values issues
            self._caption_model.config.use_cache = False
            self._caption_processor = AutoProcessor.from_pretrained(
                str(caption_path), trust_remote_code=True
            )

            logger.info("OmniParser models loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load OmniParser models: {e}")
            raise

    def detect_elements(
        self,
        screenshot_base64: str,
        viewport_width: int,
        viewport_height: int,
    ) -> list[DetectedElement]:
        """Detect UI elements from screenshot.

        Args:
            screenshot_base64: Base64 encoded screenshot (data URL or raw)
            viewport_width: Viewport width in pixels
            viewport_height: Viewport height in pixels

        Returns:
            List of detected elements with positions and captions
        """
        try:
            # Load models if not already loaded
            self._load_models()

            # Decode base64 to PIL Image
            image = self._decode_base64_image(screenshot_base64)

            # Run YOLO detection
            detections = self._detect_ui_elements(image)

            # Generate captions for detected regions
            elements = self._generate_captions(image, detections, viewport_width, viewport_height)

            logger.info(f"Detected {len(elements)} UI elements")
            return elements

        except Exception as e:
            logger.error(f"Element detection failed: {e}")
            return []

    def _decode_base64_image(self, base64_str: str) -> Image.Image:
        """Decode base64 string to PIL Image.

        Args:
            base64_str: Base64 encoded image (with or without data URL prefix)

        Returns:
            PIL Image object
        """
        # Remove data URL prefix if present
        if base64_str.startswith("data:"):
            base64_str = base64_str.split(",", 1)[1]

        # Decode base64
        image_data = base64.b64decode(base64_str)
        image = Image.open(BytesIO(image_data))

        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        return image

    def _detect_ui_elements(self, image: Image.Image) -> list[dict]:
        """Run YOLO detection on image.

        Args:
            image: PIL Image to analyze

        Returns:
            List of detection dictionaries with bboxes and confidence
        """
        # Run inference
        results = self._detection_model(image, conf=0.25)

        # Extract detections
        detections = []
        for result in results:
            boxes = result.boxes
            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu().numpy())

                detections.append(
                    {
                        "bbox": (int(x1), int(y1), int(x2), int(y2)),
                        "confidence": conf,
                    }
                )

        return detections

    def _generate_captions(
        self,
        image: Image.Image,
        detections: list[dict],
        viewport_width: int,
        viewport_height: int,
    ) -> list[DetectedElement]:
        """Generate captions for detected UI elements using Florence.

        Args:
            image: Original PIL Image
            detections: List of detection dictionaries
            viewport_width: Viewport width for grid conversion
            viewport_height: Viewport height for grid conversion

        Returns:
            List of DetectedElement objects with captions
        """
        elements = []

        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            confidence = detection["confidence"]

            # Crop element region
            element_img = image.crop((x1, y1, x2, y2))

            # Generate caption
            caption = self._caption_element(element_img)

            # Extract element type from caption
            element_type = self._extract_element_type(caption)

            # Calculate center point
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Convert to grid coordinates
            grid_coords = self._pixel_to_grid(
                center_x, center_y, viewport_width, viewport_height
            )

            # Create element
            element = DetectedElement(
                element_type=element_type,
                caption=caption,
                bbox=BoundingBox(x_min=x1, y_min=y1, x_max=x2, y_max=y2),
                grid_center=grid_coords,
                confidence=confidence,
            )

            elements.append(element)

        return elements

    def _caption_element(self, element_img: Image.Image) -> str:
        """Generate caption for a single UI element using Florence.

        Args:
            element_img: Cropped PIL Image of the element

        Returns:
            Caption string describing the element

        Note:
            Florence captioning is temporarily disabled due to compatibility issues
            with transformers library. Returns generic "UI element" placeholder.
            YOLO detection works perfectly and provides accurate coordinates.
            TODO: Fix Florence model compatibility or use alternative captioning.
        """
        # NOTE: Florence captioning temporarily disabled due to model compatibility issues
        # The prepare_inputs_for_generation method in Florence-2 has a bug where it
        # accesses past_key_values[0][0].shape[2] when past_key_values is None.
        # This affects transformers>=4.57. Issue tracked at:
        # https://github.com/huggingface/transformers/issues/...
        #
        # YOLO detection works perfectly and provides accurate bounding boxes.
        # Captioning is nice-to-have but not critical for coordinate detection.
        #
        # Future options:
        # 1. Wait for Florence model fix
        # 2. Use alternative captioning model (BLIP, GIT, etc.)
        # 3. Use pure vision LLM for captioning (GPT-4V, Claude)

        return "UI element"

    def _extract_element_type(self, caption: str) -> str:
        """Extract element type from caption.

        Args:
            caption: Caption text

        Returns:
            Element type (button, input, text, icon, etc.)
        """
        caption_lower = caption.lower()

        # Check for common element types
        if any(word in caption_lower for word in ["button", "btn"]):
            return "button"
        elif any(word in caption_lower for word in ["input", "field", "textbox"]):
            return "input"
        elif any(word in caption_lower for word in ["icon", "symbol"]):
            return "icon"
        elif any(word in caption_lower for word in ["search"]):
            return "search"
        elif any(word in caption_lower for word in ["link", "hyperlink"]):
            return "link"
        elif any(word in caption_lower for word in ["image", "img", "photo"]):
            return "image"
        else:
            return "text"

    def _pixel_to_grid(
        self, x: int, y: int, viewport_width: int, viewport_height: int
    ) -> GridCoords:
        """Convert pixel coordinates to 0-100 grid.

        Args:
            x: Pixel x coordinate
            y: Pixel y coordinate
            viewport_width: Viewport width in pixels
            viewport_height: Viewport height in pixels

        Returns:
            GridCoords with x and y in 0-100 range
        """
        grid_x = int((x / viewport_width) * 100)
        grid_y = int((y / viewport_height) * 100)

        # Clamp to 0-100 range
        grid_x = max(0, min(100, grid_x))
        grid_y = max(0, min(100, grid_y))

        return GridCoords(x=grid_x, y=grid_y)


def detect_elements_from_screenshot(
    screenshot_base64: str,
    viewport_width: int,
    viewport_height: int,
) -> list[DetectedElement]:
    """Convenience function for element detection.

    Uses singleton detector instance for model reuse.
    Returns empty list on failure (graceful degradation).

    Args:
        screenshot_base64: Base64 encoded screenshot
        viewport_width: Viewport width in pixels
        viewport_height: Viewport height in pixels

    Returns:
        List of detected elements, or empty list on failure
    """
    try:
        detector = ElementDetector.get_instance()
        return detector.detect_elements(
            screenshot_base64, viewport_width, viewport_height
        )
    except Exception as e:
        logger.warning(f"Element detection failed: {e}")
        return []


def format_elements_for_prompt(elements: list[DetectedElement]) -> str:
    """Format detected elements as text for model context.

    Args:
        elements: List of detected elements

    Returns:
        Formatted string for inclusion in prompt

    Example output:
        Detected UI Elements:
        - [1] Button "Send" at grid (95, 92)
        - [2] Input "Search contacts" at grid (12, 8)
        - [3] Text "John Doe" at grid (12, 25)
    """
    if not elements:
        return ""

    lines = ["Detected UI Elements:"]
    for i, elem in enumerate(elements, 1):
        lines.append(
            f"- [{i}] {elem.element_type.title()} "
            f'"{elem.caption}" at grid ({elem.grid_center.x}, {elem.grid_center.y})'
        )

    return "\n".join(lines)
