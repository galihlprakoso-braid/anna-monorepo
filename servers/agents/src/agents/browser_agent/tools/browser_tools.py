"""Browser automation tool definitions.

These tools define the schema for browser actions. The actual execution
happens client-side in the Chrome extension - the server only defines
what actions are available and their parameter schemas.
"""

from langchain_core.tools import tool

from agents.browser_agent.models import (
    ClickArgs,
    CollectDataArgs,
    DragArgs,
    ScreenshotArgs,
    ScrollArgs,
    TypeArgs,
    WaitArgs,
)
from agents.browser_agent.tools.skill_tools import skill_tools


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
def scroll(direction: str, amount: int = 300, x: int | None = None, y: int | None = None) -> str:
    """Scroll a specific scrollable area or the entire page.

    Use this when you need to:
    - Load older messages (scroll up in message area)
    - See more items in a list (scroll down in sidebar)
    - Access content beyond the current viewport

    IMPORTANT: Web pages can have MULTIPLE scrollable areas (sidebars, chat lists,
    message panels, content areas). To scroll a specific area, provide x,y coordinates
    targeting that area. Without coordinates, scrolls the entire page.

    Args:
        direction: One of 'up', 'down', 'left', 'right'
        amount: Number of pixels to scroll (default 300)
        x: Optional grid X coordinate (0-100) to target scrollable element at this position
        y: Optional grid Y coordinate (0-100) to target scrollable element at this position

    Examples:
        # Scroll entire page (backward compatible)
        scroll(direction='down', amount=500)

        # Scroll message area in WhatsApp (right side, X=60)
        scroll(direction='up', amount=800, x=60, y=50)

        # Scroll chat list in WhatsApp (left sidebar, X=15)
        scroll(direction='down', amount=400, x=15, y=50)

    Returns:
        Confirmation message about scroll action
    """
    # Execution happens client-side via interrupt
    if x is not None and y is not None:
        return f"Scrolled {direction} by {amount}px at grid position ({x}, {y})"
    else:
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


@tool(args_schema=CollectDataArgs)
def collect_data(data: list[str]) -> str:
    """Submit collected data from the current page for storage and processing.

    This tool accepts a list of strings containing data you extracted from the page.
    You can call this tool multiple times - it does NOT end your task.

    IMPORTANT: The 'data' parameter must be a LIST of strings, not a dict or single string.

    Args:
        data: List of strings with extracted information. Each string can be:
              - A single formatted message/item
              - A comprehensive summary string with multiple items
              Choose the format that matches the task instruction.

    Common formats:
        - Chat messages: "WhatsApp Messages | ContactName → X messages (X/20): [Sender]: text (time) | ..."
        - Individual items: ["Item 1: details", "Item 2: details", "Item 3: details"]
        - Structured data: ["Name: John, Age: 30", "Name: Jane, Age: 25"]

    Returns:
        Success message confirming how many items were collected

    Examples:
        # WhatsApp format (comprehensive string):
        collect_data(data=[
            "WhatsApp Messages | PAKE WA → 12 messages (12/20): "
            "[User]: Mau esuk ki Mas (05:47) | "
            "[PAKE WA]: Kok iso boso jowo sisan yo? (10:04) | "
            "[User]: Yo e (10:24)"
        ])

        # Individual messages:
        collect_data(data=[
            "John: Hi there (10:30 AM)",
            "Jane: Hello! (10:31 AM)",
            "Mike: How are you? (10:32 AM)"
        ])

        # Structured data:
        collect_data(data=[
            "Product: Laptop, Price: $999, Stock: 50",
            "Product: Mouse, Price: $25, Stock: 200"
        ])
    """
    # Dummy implementation - just return success
    # Future: Call ingestion pipeline endpoint
    item_count = len(data)
    return f"Successfully collected {item_count} items. Data submitted for processing."


# Export all browser tools as a list for binding to the model
browser_tools = [
    click,
    type_text,
    scroll,
    drag,
    wait,
    screenshot,
    collect_data,
] + skill_tools
