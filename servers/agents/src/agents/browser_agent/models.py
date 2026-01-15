"""Pydantic models for browser tool arguments.

These models define the schema for browser automation tool parameters,
using Pydantic for validation and OpenAPI schema generation.
"""

from typing import Optional
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
    """Scroll a specific area or the entire page."""

    direction: str = Field(description="Direction: up, down, left, right")
    amount: int = Field(default=300, ge=0, description="Scroll amount in pixels")
    x: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "Optional X coordinate (0-100 grid) to target specific scrollable area. "
            "If provided with y, scrolls the element at this position. "
            "If omitted, scrolls entire page. "
            "Example: x=60 for WhatsApp message area, x=15 for chat list"
        ),
    )
    y: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "Optional Y coordinate (0-100 grid) to target specific scrollable area. "
            "If provided with x, scrolls the element at this position. "
            "If omitted, scrolls entire page. "
            "Example: y=50 for middle of screen"
        ),
    )


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


class LoadSkillArgs(BaseModel):
    """Load a specialized skill prompt for domain-specific tasks."""

    skill_name: str = Field(
        description=(
            "REQUIRED: Name of the skill to load. Must be one of the available skills. "
            "Common skills: 'whatsapp-web' for WhatsApp Web automation. "
            "Example: skill_name='whatsapp-web'"
        )
    )


class CollectDataArgs(BaseModel):
    """Collect and submit data from the page."""

    data: list[str] = Field(
        description=(
            "List of strings where each string contains data you want to submit. "
            "You can submit a single comprehensive string with all collected items, "
            "or multiple strings (one per item). "
            "Example for WhatsApp: ['WhatsApp Messages | PAKE WA → 12 messages (12/20): [User]: Hi (10:04) | [PAKE WA]: Hello (10:05)'] "
            "or ['Message 1: Hi (10:04)', 'Message 2: Hello (10:05)']"
        )
    )
