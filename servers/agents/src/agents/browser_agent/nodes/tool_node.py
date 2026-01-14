"""Tool node for the browser automation agent.

This node handles tool execution via two different mechanisms:
1. Server-side tools (load_skill, collect_data) - executed directly
2. Client-side tools (click, type, scroll, etc.) - executed via interrupts
"""

import logging
from dataclasses import asdict

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt

from agents.browser_agent.state import AgentState, BrowserToolCall, BrowserToolResult, Viewport

logger = logging.getLogger(__name__)

# Server-side tools that should NOT be interrupted
SERVER_SIDE_TOOLS = {"load_skill", "collect_data"}


def tool_node(state: AgentState) -> dict:
    """Tool execution node with hybrid server/client execution.

    This node:
    1. Extracts tool call from last AI message
    2. Determines if it's server-side or client-side
    3. Either executes directly or creates interrupt for client execution
    4. Returns tool message with result

    Uses isinstance() for type checking instead of hasattr() for proper typing.

    Args:
        state: Current agent state containing messages

    Returns:
        Dictionary with tool result message and updated screenshot/viewport
    """
    messages = state.messages

    if not messages:
        return {}

    last_message = messages[-1]

    # Use isinstance() for type checking - NOT hasattr()
    if not isinstance(last_message, AIMessage):
        return {}

    # AIMessage always has tool_calls attribute (list, possibly empty)
    tool_calls = last_message.tool_calls
    if not tool_calls:
        return {}

    # Process the first tool call
    # (could be extended to handle multiple tool calls)
    tool_call = tool_calls[0]
    tool_name = tool_call["name"]  # type: ignore[arg-type]

    # Check if this is a server-side tool
    if tool_name in SERVER_SIDE_TOOLS:
        return _execute_server_side_tool(tool_call)

    # Otherwise, interrupt for client-side execution
    return _execute_client_side_tool(tool_call)


def _execute_server_side_tool(tool_call: dict) -> dict:
    """Execute server-side tools directly without interrupt.

    Server-side tools are executed in the Python process and don't
    require browser interaction. This includes tools like:
    - load_skill: Loads prompt files from server filesystem
    - collect_data: Processes collected data

    Args:
        tool_call: Dictionary with tool name, args, and id

    Returns:
        Dictionary with tool message containing result
    """
    tool_name = tool_call["name"]
    args = tool_call["args"]

    logger.info(f"Executing server-side tool: {tool_name} with args: {args}")

    if tool_name == "load_skill":
        from agents.browser_agent.tools.skill_tools import load_skill
        result = load_skill.invoke(args)
        logger.info(f"load_skill returned {len(result)} characters")
    elif tool_name == "collect_data":
        from agents.browser_agent.tools.browser_tools import collect_data
        result = collect_data.invoke(args)
        logger.info(f"collect_data result: {result}")
    else:
        result = f"Unknown server-side tool: {tool_name}"
        logger.warning(result)

    # Create tool result message
    tool_message = ToolMessage(
        content=result,
        tool_call_id=tool_call["id"],
    )

    return {"messages": [tool_message]}


def _execute_client_side_tool(tool_call: dict) -> dict:
    """Create interrupt for client-side browser action execution.

    Client-side tools require browser interaction and are executed
    in the Chrome extension context. This includes:
    - click, type_text, scroll, drag, wait, screenshot

    The function:
    1. Creates interrupt payload with tool info
    2. Pauses execution and waits for client
    3. Receives result when client resumes
    4. Returns tool message with result

    Args:
        tool_call: Dictionary with tool name, args, and id

    Returns:
        Dictionary with tool message and updated screenshot/viewport
    """
    logger.info(f"Executing client-side tool: {tool_call['name']} with args: {tool_call['args']}")

    # Create interrupt payload for client
    interrupt_payload = BrowserToolCall(
        action=tool_call["name"],  # type: ignore[arg-type]
        args=tool_call["args"],
        request_screenshot=True,  # Always request screenshot after action
    )
    
    logger.info(f"Creating interrupt for action: {interrupt_payload.action}")

    # Pause execution and wait for client to execute the action
    # Client will resume with BrowserToolResult as a dict
    result_dict: dict = interrupt(asdict(interrupt_payload))

    # Convert result dict to BrowserToolResult dataclass
    viewport = None
    if result_dict.get("viewport"):
        viewport_data = result_dict["viewport"]
        viewport = Viewport(
            width=viewport_data["width"],
            height=viewport_data["height"],
        )

    result = BrowserToolResult(
        result=result_dict["result"],
        screenshot=result_dict.get("screenshot"),
        viewport=viewport,
    )

    # Create tool result message
    tool_message = ToolMessage(
        content=result.result,
        tool_call_id=tool_call["id"],
    )

    # Build updates dictionary
    updates: dict = {"messages": [tool_message]}

    # Update state with new screenshot if provided
    if result.screenshot is not None:
        updates["current_screenshot"] = result.screenshot
        # Clear old elements - will be re-detected in next iteration
        updates["detected_elements"] = []

    if result.viewport is not None:
        updates["viewport"] = result.viewport

    return updates
