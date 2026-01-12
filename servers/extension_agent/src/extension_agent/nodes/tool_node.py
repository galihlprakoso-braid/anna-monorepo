"""Tool node for the browser automation agent.

This node handles tool execution via LangGraph interrupts. When the model
requests a tool call, this node creates an interrupt that pauses execution
and sends the tool request to the client (Chrome extension). The client
executes the action and resumes with the result.
"""

from dataclasses import asdict

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt

from extension_agent.state import AgentState, BrowserToolCall, BrowserToolResult, Viewport


def tool_node(state: AgentState) -> dict:
    """Tool execution node using interrupt for client-side execution.

    This node:
    1. Extracts tool call from last AI message
    2. Creates interrupt to request client execution
    3. Receives result when client resumes
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

    # Create interrupt payload for client
    interrupt_payload = BrowserToolCall(
        action=tool_call["name"],  # type: ignore[arg-type]
        args=tool_call["args"],
        request_screenshot=True,  # Always request screenshot after action
    )

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

    if result.viewport is not None:
        updates["viewport"] = result.viewport

    return updates
