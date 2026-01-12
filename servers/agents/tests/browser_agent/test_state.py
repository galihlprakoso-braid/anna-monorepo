"""Tests for state dataclasses."""

from dataclasses import asdict

from agents.browser_agent.state import (
    AgentState,
    BrowserToolCall,
    BrowserToolResult,
    Viewport,
)


def test_viewport_creation():
    """Test Viewport dataclass creation."""
    viewport = Viewport(width=1920, height=1080)
    assert viewport.width == 1920
    assert viewport.height == 1080


def test_viewport_is_frozen():
    """Test that Viewport is immutable."""
    viewport = Viewport(width=1920, height=1080)
    try:
        viewport.width = 1280  # type: ignore[misc]
        assert False, "Should have raised FrozenInstanceError"
    except Exception:
        pass  # Expected


def test_browser_tool_call_creation():
    """Test BrowserToolCall dataclass creation."""
    tool_call = BrowserToolCall(
        action="click",
        args={"x": 50, "y": 50},
        request_screenshot=True,
    )
    assert tool_call.action == "click"
    assert tool_call.args == {"x": 50, "y": 50}
    assert tool_call.request_screenshot is True


def test_browser_tool_call_default_screenshot():
    """Test BrowserToolCall defaults to requesting screenshot."""
    tool_call = BrowserToolCall(action="type", args={"text": "hello"})
    assert tool_call.request_screenshot is True


def test_browser_tool_call_to_dict():
    """Test BrowserToolCall can be converted to dict for serialization."""
    tool_call = BrowserToolCall(
        action="scroll",
        args={"direction": "down", "amount": 300},
    )
    result = asdict(tool_call)
    assert result == {
        "action": "scroll",
        "args": {"direction": "down", "amount": 300},
        "request_screenshot": True,
    }


def test_browser_tool_result_creation():
    """Test BrowserToolResult dataclass creation."""
    viewport = Viewport(width=1920, height=1080)
    result = BrowserToolResult(
        result="Clicked at (50, 50)",
        screenshot="base64_data_here",
        viewport=viewport,
    )
    assert result.result == "Clicked at (50, 50)"
    assert result.screenshot == "base64_data_here"
    assert result.viewport is not None
    assert result.viewport.width == 1920


def test_browser_tool_result_optional_fields():
    """Test BrowserToolResult with optional fields as None."""
    result = BrowserToolResult(result="Action completed")
    assert result.result == "Action completed"
    assert result.screenshot is None
    assert result.viewport is None


def test_agent_state_creation():
    """Test AgentState dataclass creation."""
    state = AgentState()
    assert state.messages == []
    assert state.current_screenshot is None
    assert state.viewport is None


def test_agent_state_with_viewport():
    """Test AgentState with viewport."""
    viewport = Viewport(width=1280, height=720)
    state = AgentState(
        current_screenshot="base64_screenshot",
        viewport=viewport,
    )
    assert state.current_screenshot == "base64_screenshot"
    assert state.viewport is not None
    assert state.viewport.width == 1280
