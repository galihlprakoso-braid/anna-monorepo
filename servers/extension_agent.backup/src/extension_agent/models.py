"""Pydantic models for browser tool arguments.

These models define the schema for browser automation tool parameters,
using Pydantic for validation and OpenAPI schema generation.
"""

from pydantic import BaseModel, Field


class ClickArgs(BaseModel):
    """Click at a position using 0-100 grid coordinates."""

    x: int = Field(
        ge=0, le=100, description="X position (0=left, 50=center, 100=right)"
    )
    y: int = Field(
        ge=0, le=100, description="Y position (0=top, 50=center, 100=bottom)"
    )


class TypeArgs(BaseModel):
    """Type text at current cursor position."""

    text: str = Field(description="Text to type")


class ScrollArgs(BaseModel):
    """Scroll the page in a direction."""

    direction: str = Field(description="Direction: up, down, left, right")
    amount: int = Field(default=300, ge=0, description="Scroll amount in pixels")


class DragArgs(BaseModel):
    """Drag from one position to another using grid coordinates."""

    start_x: int = Field(ge=0, le=100, description="Start X position (0-100)")
    start_y: int = Field(ge=0, le=100, description="Start Y position (0-100)")
    end_x: int = Field(ge=0, le=100, description="End X position (0-100)")
    end_y: int = Field(ge=0, le=100, description="End Y position (0-100)")


class WaitArgs(BaseModel):
    """Wait for a duration."""

    ms: int = Field(ge=0, le=10000, description="Wait time in milliseconds")


class ScreenshotArgs(BaseModel):
    """Request a new screenshot of the current page."""

    reason: str = Field(default="", description="Reason for requesting screenshot")
