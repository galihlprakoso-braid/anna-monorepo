"""Model node for the browser automation agent.

This node invokes the LLM to decide what action to take based on
the current state (messages, screenshot).
"""

from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from agents.browser_agent.state import AgentState
from agents.browser_agent.tools.browser_tools import browser_tools
from agents.shared.prompt_loader import load_prompt

# Path to system prompt (relative to this file)
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system.prompt.md"

# Lazy model initialization - only create when needed
# Using GPT-5-mini for good vision + reasoning balance
_model = None
_system_prompt = None


def get_system_prompt() -> str:
    """Get or load the system prompt.

    Lazy loading ensures file is only read once and cached in memory.
    """
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = load_prompt(SYSTEM_PROMPT_PATH)
    return _system_prompt


def get_model():
    """Get or create the model instance with tools bound.

    This lazy initialization ensures API key is only required when actually using the model.
    """
    global _model
    if _model is None:
        _model = ChatOpenAI(model="gpt-5-mini").bind_tools(browser_tools)
    return _model


def model_node(state: AgentState) -> dict:
    """LLM reasoning node - decides what action to take.

    This node:
    1. Takes the current conversation messages
    2. Adds the system prompt (with detected elements if available)
    3. Invokes the model to get a response
    4. Returns the response (which may include tool calls)

    Args:
        state: Current agent state containing messages and screenshot

    Returns:
        Dictionary with the new message to append to state
    """
    messages = state.messages

    # Build system prompt with detected elements
    base_prompt = get_system_prompt()

    # Add detected elements context if available
    elements_context = ""
    if state.detected_elements:
        from agents.browser_agent.services.element_detector import (
            format_elements_for_prompt,
        )

        elements_context = "\n\n" + format_elements_for_prompt(state.detected_elements)

    full_prompt = base_prompt + elements_context

    # Create system message with enriched prompt
    system_message = SystemMessage(content=full_prompt)

    # Get model instance and invoke with system message + conversation messages
    model = get_model()
    response = model.invoke([system_message] + list(messages))

    return {"messages": [response]}
