"""Browser automation tool definitions.

These tools define the schema for browser actions. The actual execution
happens client-side in the Chrome extension - the server only defines
what actions are available and their parameter schemas.
"""

from langchain_core.tools import tool

from extension_agent.models import (
    ClickArgs,
    DragArgs,
    ScreenshotArgs,
    ScrollArgs,
    TypeArgs,
    WaitArgs,
)


@tool(args_schema=ClickArgs)
def click(x: int, y: int) -> str:
    """Click at position on screen using grid coordinates (0-100 scale).

    The coordinate system maps 0-100 to the viewport dimensions:
    - (0, 0) is the top-left corner
    - (50, 50) is the center
    - (100, 100) is the bottom-right corner
    """
    # Execution happens client-side via interrupt
    return f"Clicked at ({x}, {y})"


@tool(args_schema=TypeArgs)
def type_text(text: str) -> str:
    """Type text at current cursor position.

    Use this after clicking on an input field or text area.
    """
    # Execution happens client-side via interrupt
    return f"Typed: {text}"


@tool(args_schema=ScrollArgs)
def scroll(direction: str, amount: int = 300) -> str:
    """Scroll the page in specified direction.

    Args:
        direction: One of 'up', 'down', 'left', 'right'
        amount: Number of pixels to scroll (default 300)
    """
    # Execution happens client-side via interrupt
    return f"Scrolled {direction} by {amount}px"


@tool(args_schema=DragArgs)
def drag(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    """Drag from start position to end position using grid coordinates.

    Useful for drag-and-drop operations, selecting text, or
    moving elements.
    """
    # Execution happens client-side via interrupt
    return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"


@tool(args_schema=WaitArgs)
def wait(ms: int) -> str:
    """Wait for specified milliseconds.

    Use this to wait for page animations, loading states,
    or other async operations.
    """
    # Execution happens client-side via interrupt
    return f"Waited {ms}ms"


@tool(args_schema=ScreenshotArgs)
def screenshot(reason: str = "") -> str:
    """Request a fresh screenshot of the current page.

    Use this when you need to see the current state of the page,
    especially after an action that might have changed the content.
    """
    # Execution happens client-side via interrupt
    return f"Screenshot requested: {reason}" if reason else "Screenshot requested"


# Export all browser tools as a list for binding to the model
browser_tools = [click, type_text, scroll, drag, wait, screenshot]
