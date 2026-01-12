"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from agents.browser_agent.models import (
    ClickArgs,
    DragArgs,
    ScreenshotArgs,
    ScrollArgs,
    TypeArgs,
    WaitArgs,
)


class TestClickArgs:
    """Tests for ClickArgs model."""

    def test_valid_click(self):
        """Test valid click coordinates."""
        args = ClickArgs(x=50, y=50)
        assert args.x == 50
        assert args.y == 50

    def test_click_bounds(self):
        """Test click at boundary values."""
        # Min values
        args_min = ClickArgs(x=0, y=0)
        assert args_min.x == 0
        assert args_min.y == 0

        # Max values
        args_max = ClickArgs(x=100, y=100)
        assert args_max.x == 100
        assert args_max.y == 100

    def test_click_invalid_x_below(self):
        """Test click with x below valid range."""
        with pytest.raises(ValidationError):
            ClickArgs(x=-1, y=50)

    def test_click_invalid_x_above(self):
        """Test click with x above valid range."""
        with pytest.raises(ValidationError):
            ClickArgs(x=101, y=50)

    def test_click_invalid_y_below(self):
        """Test click with y below valid range."""
        with pytest.raises(ValidationError):
            ClickArgs(x=50, y=-1)

    def test_click_invalid_y_above(self):
        """Test click with y above valid range."""
        with pytest.raises(ValidationError):
            ClickArgs(x=50, y=101)


class TestTypeArgs:
    """Tests for TypeArgs model."""

    def test_valid_type(self):
        """Test valid text input."""
        args = TypeArgs(text="Hello, World!")
        assert args.text == "Hello, World!"

    def test_empty_text(self):
        """Test empty text is valid."""
        args = TypeArgs(text="")
        assert args.text == ""

    def test_special_characters(self):
        """Test text with special characters."""
        args = TypeArgs(text="Special chars: @#$%^&*()")
        assert "@#$%^&*()" in args.text


class TestScrollArgs:
    """Tests for ScrollArgs model."""

    def test_scroll_with_default_amount(self):
        """Test scroll with default amount."""
        args = ScrollArgs(direction="down")
        assert args.direction == "down"
        assert args.amount == 300

    def test_scroll_with_custom_amount(self):
        """Test scroll with custom amount."""
        args = ScrollArgs(direction="up", amount=500)
        assert args.direction == "up"
        assert args.amount == 500

    def test_scroll_invalid_amount(self):
        """Test scroll with negative amount."""
        with pytest.raises(ValidationError):
            ScrollArgs(direction="down", amount=-100)


class TestDragArgs:
    """Tests for DragArgs model."""

    def test_valid_drag(self):
        """Test valid drag coordinates."""
        args = DragArgs(start_x=10, start_y=20, end_x=80, end_y=90)
        assert args.start_x == 10
        assert args.start_y == 20
        assert args.end_x == 80
        assert args.end_y == 90

    def test_drag_same_position(self):
        """Test drag to same position (valid but no-op)."""
        args = DragArgs(start_x=50, start_y=50, end_x=50, end_y=50)
        assert args.start_x == args.end_x
        assert args.start_y == args.end_y

    def test_drag_invalid_coordinates(self):
        """Test drag with invalid coordinates."""
        with pytest.raises(ValidationError):
            DragArgs(start_x=-1, start_y=50, end_x=50, end_y=50)


class TestWaitArgs:
    """Tests for WaitArgs model."""

    def test_valid_wait(self):
        """Test valid wait time."""
        args = WaitArgs(ms=1000)
        assert args.ms == 1000

    def test_wait_zero(self):
        """Test zero wait time is valid."""
        args = WaitArgs(ms=0)
        assert args.ms == 0

    def test_wait_max(self):
        """Test maximum wait time."""
        args = WaitArgs(ms=10000)
        assert args.ms == 10000

    def test_wait_exceeds_max(self):
        """Test wait time exceeding maximum."""
        with pytest.raises(ValidationError):
            WaitArgs(ms=10001)

    def test_wait_negative(self):
        """Test negative wait time."""
        with pytest.raises(ValidationError):
            WaitArgs(ms=-1)


class TestScreenshotArgs:
    """Tests for ScreenshotArgs model."""

    def test_screenshot_with_reason(self):
        """Test screenshot with reason."""
        args = ScreenshotArgs(reason="Check form submission result")
        assert args.reason == "Check form submission result"

    def test_screenshot_default_reason(self):
        """Test screenshot with default empty reason."""
        args = ScreenshotArgs()
        assert args.reason == ""
