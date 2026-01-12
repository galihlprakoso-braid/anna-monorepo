"""Model node for the browser automation agent.

This node invokes the LLM to decide what action to take based on
the current state (messages, screenshot).
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from extension_agent.prompts.system import SYSTEM_PROMPT
from extension_agent.state import AgentState
from extension_agent.tools.browser_tools import browser_tools

# Lazy model initialization - only create when needed
# Using GPT-4o for good vision + reasoning balance
_model = None


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
    2. Adds the system prompt
    3. Invokes the model to get a response
    4. Returns the response (which may include tool calls)

    Args:
        state: Current agent state containing messages and screenshot

    Returns:
        Dictionary with the new message to append to state
    """
    messages = state.messages

    # Create system message with the browser automation prompt
    system_message = SystemMessage(content=SYSTEM_PROMPT)

    # Get model instance and invoke with system message + conversation messages
    model = get_model()
    response = model.invoke([system_message] + list(messages))

    return {"messages": [response]}
