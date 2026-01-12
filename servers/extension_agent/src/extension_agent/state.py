"""State definitions for the browser automation agent.

Uses dataclasses instead of TypedDict for proper typing and IDE support.
"""

from dataclasses import dataclass, field
from typing import Annotated, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# Browser action types
BrowserAction = Literal["click", "type", "scroll", "drag", "wait", "screenshot"]


@dataclass(frozen=True)
class Viewport:
    """Browser viewport dimensions."""

    width: int
    height: int


@dataclass(frozen=True)
class BrowserToolCall:
    """Tool call that will be sent to client via interrupt.

    This is the payload sent to the Chrome extension when the agent
    decides to perform a browser action.
    """

    action: BrowserAction
    args: dict[str, int | str | float]
    request_screenshot: bool = True


@dataclass(frozen=True)
class BrowserToolResult:
    """Result returned from client after executing tool.

    This is sent back from the Chrome extension after executing
    the browser action.
    """

    result: str
    screenshot: str | None = None  # base64 encoded
    viewport: Viewport | None = None


@dataclass
class AgentState:
    """Main agent state for the browser automation graph.

    Uses Annotated with add_messages for proper message list management
    in LangGraph.
    """

    messages: Annotated[list[BaseMessage], add_messages] = field(default_factory=list)
    current_screenshot: str | None = None  # Latest screenshot (base64)
    viewport: Viewport | None = None  # Current viewport dimensions
