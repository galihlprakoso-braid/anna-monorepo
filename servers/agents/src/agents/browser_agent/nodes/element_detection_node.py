"""Element detection node for preprocessing screenshots.

This node runs after receiving a new screenshot and before the model node,
detecting UI elements to enrich the model's context.
"""

import os

from agents.browser_agent.state import AgentState


# Feature flag for easy disable
ELEMENT_DETECTION_ENABLED = (
    os.environ.get("ELEMENT_DETECTION_ENABLED", "true").lower() == "true"
)


def element_detection_node(state: AgentState) -> dict:
    """Detect UI elements from current screenshot.

    This node:
    1. Checks if element detection is enabled
    2. Extracts current screenshot and viewport from state
    3. Runs element detection
    4. Returns detected elements to update state

    Returns empty list if detection disabled or fails.

    Args:
        state: Current agent state containing screenshot and viewport

    Returns:
        Dictionary with detected_elements to update state
    """
    # Skip if disabled via feature flag
    if not ELEMENT_DETECTION_ENABLED:
        return {"detected_elements": []}

    # Skip if no screenshot available
    if not state.current_screenshot or not state.viewport:
        return {"detected_elements": []}

    # Import here to avoid loading models until needed
    from agents.browser_agent.services.element_detector import (
        detect_elements_from_screenshot,
    )

    # Handle viewport - can be dict (from client input) or Viewport dataclass
    if isinstance(state.viewport, dict):
        viewport_width = state.viewport["width"]
        viewport_height = state.viewport["height"]
    else:
        viewport_width = state.viewport.width
        viewport_height = state.viewport.height

    # Detect elements (returns empty list on failure)
    elements = detect_elements_from_screenshot(
        screenshot_base64=state.current_screenshot,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )

    return {"detected_elements": elements}
