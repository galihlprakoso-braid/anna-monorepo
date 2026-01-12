"""Chat agent for ANNA - a simple conversational assistant.

This agent uses create_agent for a production-ready conversational assistant.
The agent provides friendly parenting assistance without tool calling.
"""

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from pathlib import Path
from agents.shared.prompt_loader import load_prompt

# Path to system prompt
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.prompt.md"

# Lazy initialization
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
    """Get or create the model instance.

    This lazy initialization ensures API key is only required when actually using the model.
    """
    global _model
    if _model is None:
        _model = ChatOpenAI(model="gpt-4o")
    return _model


# Create the agent using create_agent
# This provides a production-ready agent with built-in message handling
# NOTE: When using LangGraph API (langgraph dev), persistence is handled automatically
# The platform provides checkpointing and thread management
graph = create_agent(
    model=get_model(),
    tools=[],  # No tools - pure conversation agent
    system_prompt=get_system_prompt()
)
