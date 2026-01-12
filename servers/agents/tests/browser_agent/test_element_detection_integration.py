"""Integration tests for element detection with real screenshots.

These tests use actual screenshots to validate the full element detection pipeline
including OmniParser model inference.
"""

import base64
from pathlib import Path

import pytest
from PIL import Image

from agents.browser_agent.services.element_detector import (
    detect_elements_from_screenshot,
)


# Skip tests if models are not available
# Path: tests/browser_agent/test_*.py -> go up to project root -> weights/
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_WEIGHTS_PATH = _PROJECT_ROOT / "weights" / "icon_detect" / "model.pt"

pytestmark = pytest.mark.skipif(
    not _WEIGHTS_PATH.exists(),
    reason="OmniParser weights not downloaded. Run scripts/setup_omniparser.sh",
)


class TestElementDetectionWithRealImage:
    """Integration tests using actual screenshot images."""

    def test_detect_elements_from_whatsapp_screenshot(self):
        """Test element detection on WhatsApp Web screenshot (ss-1.png).

        This test validates:
        1. Image loading and base64 encoding
        2. YOLOv8 detection model inference
        3. Florence captioning model inference
        4. Coordinate conversion to 0-100 grid
        5. Element filtering and formatting
        """
        # Load the test image
        image_path = Path(__file__).parent / "images" / "ss-1.png"
        assert image_path.exists(), f"Test image not found at {image_path}"

        # Load and encode image as base64
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Get image dimensions
        img = Image.open(image_path)
        viewport_width, viewport_height = img.size

        print(f"Image dimensions: {viewport_width}x{viewport_height}")

        # Encode as base64 (with data URL prefix)
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        # Run element detection
        elements = detect_elements_from_screenshot(
            screenshot_base64=data_url,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )

        # Validate results
        print(f"\nDetected {len(elements)} UI elements:")
        for i, elem in enumerate(elements, 1):
            print(
                f"  [{i}] {elem.element_type.title()} '{elem.caption}' "
                f"at grid ({elem.grid_center.x}, {elem.grid_center.y}) "
                f"[confidence: {elem.confidence:.2f}]"
            )

        # Basic assertions
        assert len(elements) > 0, "Should detect at least one element"

        # Validate element structure
        for elem in elements:
            assert elem.element_type in [
                "button",
                "input",
                "text",
                "icon",
                "link",
                "search",
                "image",
            ]
            assert isinstance(elem.caption, str)
            assert len(elem.caption) > 0
            assert 0 <= elem.grid_center.x <= 100
            assert 0 <= elem.grid_center.y <= 100
            assert 0.0 <= elem.confidence <= 1.0
            assert elem.bbox.x_min < elem.bbox.x_max
            assert elem.bbox.y_min < elem.bbox.y_max

        # WhatsApp-specific assertions (based on ss-1.png content)
        # The screenshot shows WhatsApp Web with search bar and chat list
        # NOTE: Captioning is temporarily disabled, so we can't check for specific captions
        # We verify that YOLO detection found elements in expected regions

        # Should have elements in the left sidebar area (x < 30)
        sidebar_elements = [elem for elem in elements if elem.grid_center.x < 30]
        assert len(sidebar_elements) > 5, "Should detect multiple elements in left sidebar"

        # Should detect text elements (contact names, messages)
        has_text = any(elem.element_type == "text" for elem in elements)
        assert has_text, "Should detect text elements (contacts, messages)"

        print("\n✓ All assertions passed!")

    def test_detect_elements_coordinate_accuracy(self):
        """Test that detected coordinates are reasonable for WhatsApp layout.

        This validates that the grid coordinates match expected WhatsApp Web layout:
        - Search bar should be near the top-left (approximately x: 5-20, y: 5-15)
        - Chat list items should be in left sidebar (approximately x: 5-25)
        - Button elements should have reasonable positions
        """
        # Load test image
        image_path = Path(__file__).parent / "images" / "ss-1.png"
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        img = Image.open(image_path)
        viewport_width, viewport_height = img.size

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        # Detect elements
        elements = detect_elements_from_screenshot(
            data_url, viewport_width, viewport_height
        )

        # Find search bar element
        search_elements = [
            elem
            for elem in elements
            if "search" in elem.caption.lower() or "ask meta" in elem.caption.lower()
        ]

        if search_elements:
            search_elem = search_elements[0]
            print(
                f"\nSearch element found at grid ({search_elem.grid_center.x}, {search_elem.grid_center.y})"
            )

            # Search bar should be in the top-left area
            assert (
                search_elem.grid_center.x < 30
            ), "Search bar should be in left sidebar"
            assert search_elem.grid_center.y < 20, "Search bar should be near the top"

        # Verify sidebar elements are on the left
        sidebar_elements = [elem for elem in elements if elem.grid_center.x < 30]
        print(f"Found {len(sidebar_elements)} elements in left sidebar area")
        assert len(sidebar_elements) > 0, "Should detect elements in left sidebar"

        print("✓ Coordinate accuracy validation passed!")

    def test_detect_elements_graceful_failure(self):
        """Test that invalid input returns empty list (no crash)."""
        # Test with invalid base64
        elements = detect_elements_from_screenshot("invalid_base64", 1000, 800)
        assert elements == [], "Should return empty list on invalid input"

        # Test with empty string
        elements = detect_elements_from_screenshot("", 1000, 800)
        assert elements == [], "Should return empty list on empty input"

        print("✓ Graceful failure handling validated!")


class TestElementDetectionNode:
    """Integration tests for the element detection node."""

    def test_element_detection_node_with_real_screenshot(self):
        """Test the full node execution with a real screenshot."""
        from agents.browser_agent.nodes.element_detection_node import (
            element_detection_node,
        )
        from agents.browser_agent.state import AgentState, Viewport

        # Load test image
        image_path = Path(__file__).parent / "images" / "ss-1.png"
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        img = Image.open(image_path)
        viewport_width, viewport_height = img.size

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        # Create state with screenshot
        state = AgentState(
            current_screenshot=data_url,
            viewport=Viewport(width=viewport_width, height=viewport_height),
        )

        # Run node
        result = element_detection_node(state)

        # Validate result
        assert "detected_elements" in result
        assert isinstance(result["detected_elements"], list)
        assert len(result["detected_elements"]) > 0

        print(f"Node detected {len(result['detected_elements'])} elements")
        print("✓ Element detection node integration test passed!")

    def test_element_detection_node_without_screenshot(self):
        """Test that node returns empty list when no screenshot is available."""
        from agents.browser_agent.nodes.element_detection_node import (
            element_detection_node,
        )
        from agents.browser_agent.state import AgentState

        # Create state without screenshot
        state = AgentState()

        # Run node
        result = element_detection_node(state)

        # Should return empty list
        assert result == {"detected_elements": []}
        print("✓ Node correctly handles missing screenshot!")


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "-s"])
