"""Unit tests for element detector service."""

import base64
from pathlib import Path

import pytest
from PIL import Image

from agents.browser_agent.services.element_detector import (
    DetectedElement,
    ElementDetector,
    format_elements_for_prompt,
)
from agents.browser_agent.state import BoundingBox, GridCoords


class TestCoordinateConversion:
    """Test pixel to grid coordinate conversion."""

    def test_pixel_to_grid_center(self):
        """Test conversion of center pixel to grid."""
        detector = ElementDetector()
        grid = detector._pixel_to_grid(500, 400, 1000, 800)

        assert grid.x == 50
        assert grid.y == 50

    def test_pixel_to_grid_top_left(self):
        """Test conversion of top-left corner."""
        detector = ElementDetector()
        grid = detector._pixel_to_grid(0, 0, 1000, 800)

        assert grid.x == 0
        assert grid.y == 0

    def test_pixel_to_grid_bottom_right(self):
        """Test conversion of bottom-right corner."""
        detector = ElementDetector()
        grid = detector._pixel_to_grid(1000, 800, 1000, 800)

        assert grid.x == 100
        assert grid.y == 100

    def test_pixel_to_grid_clamping(self):
        """Test that coordinates are clamped to 0-100."""
        detector = ElementDetector()

        # Test negative values
        grid = detector._pixel_to_grid(-10, -10, 1000, 800)
        assert grid.x == 0
        assert grid.y == 0

        # Test values exceeding bounds
        grid = detector._pixel_to_grid(1100, 900, 1000, 800)
        assert grid.x == 100
        assert grid.y == 100


class TestFormatElements:
    """Test element formatting for prompts."""

    def test_format_empty_elements(self):
        """Test formatting with no elements."""
        result = format_elements_for_prompt([])
        assert result == ""

    def test_format_single_element(self):
        """Test formatting with one element."""
        elements = [
            DetectedElement(
                element_type="button",
                caption="Send",
                bbox=BoundingBox(x_min=900, y_min=700, x_max=950, y_max=750),
                grid_center=GridCoords(x=95, y=92),
                confidence=0.95,
            )
        ]

        result = format_elements_for_prompt(elements)

        assert "Detected UI Elements:" in result
        assert "[1] Button" in result
        assert '"Send"' in result
        assert "(95, 92)" in result

    def test_format_multiple_elements(self):
        """Test formatting with multiple elements."""
        elements = [
            DetectedElement(
                element_type="button",
                caption="Send",
                bbox=BoundingBox(x_min=900, y_min=700, x_max=950, y_max=750),
                grid_center=GridCoords(x=95, y=92),
                confidence=0.95,
            ),
            DetectedElement(
                element_type="input",
                caption="Search",
                bbox=BoundingBox(x_min=100, y_min=50, x_max=200, y_max=80),
                grid_center=GridCoords(x=12, y=8),
                confidence=0.88,
            ),
        ]

        result = format_elements_for_prompt(elements)

        assert "[1]" in result
        assert "[2]" in result
        assert "Button" in result
        assert "Input" in result
        assert "Send" in result
        assert "Search" in result


class TestElementDetector:
    """Test element detector functionality."""

    def test_singleton_pattern(self):
        """Test that get_instance returns the same instance."""
        instance1 = ElementDetector.get_instance()
        instance2 = ElementDetector.get_instance()

        assert instance1 is instance2

    def test_decode_base64_image_with_data_url(self):
        """Test decoding base64 with data URL prefix."""
        # Create a simple 1x1 red pixel image
        img = Image.new("RGB", (1, 1), color="red")
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        # Encode as base64 with data URL prefix
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        detector = ElementDetector()
        decoded = detector._decode_base64_image(data_url)

        assert decoded.mode == "RGB"
        assert decoded.size == (1, 1)

    def test_decode_base64_image_raw(self):
        """Test decoding raw base64 without data URL prefix."""
        # Create a simple 1x1 blue pixel image
        img = Image.new("RGB", (1, 1), color="blue")
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        # Encode as base64 without prefix
        b64 = base64.b64encode(img_bytes).decode("utf-8")

        detector = ElementDetector()
        decoded = detector._decode_base64_image(b64)

        assert decoded.mode == "RGB"
        assert decoded.size == (1, 1)

    def test_extract_element_type_button(self):
        """Test element type extraction for buttons."""
        detector = ElementDetector()

        assert detector._extract_element_type("Send button") == "button"
        assert detector._extract_element_type("Click this btn") == "button"

    def test_extract_element_type_input(self):
        """Test element type extraction for inputs."""
        detector = ElementDetector()

        assert detector._extract_element_type("Search input field") == "input"
        assert detector._extract_element_type("Text field") == "input"

    def test_extract_element_type_default(self):
        """Test element type extraction defaults to text."""
        detector = ElementDetector()

        assert detector._extract_element_type("Some random caption") == "text"
