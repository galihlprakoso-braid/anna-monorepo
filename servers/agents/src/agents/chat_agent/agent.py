"""Chat agent for ANNA - a simple conversational assistant.

This agent uses a simple StateGraph pattern for reliable conversation.
The agent provides friendly parenting assistance without tool calling.
"""

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph, MessagesState

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


def model_node(state: MessagesState) -> dict:
    """LLM conversation node - generates responses to user messages.

    This node:
    1. Takes the current conversation messages
    2. Adds the system prompt with Anna's personality
    3. Invokes the model to get a response
    4. Returns the response

    Args:
        state: Current state containing messages

    Returns:
        Dictionary with the new message to append to state
    """
    messages = state["messages"]

    # Create system message with Anna's personality
    system_message = SystemMessage(content=get_system_prompt())

    # Get model instance and invoke with system message + conversation messages
    model = get_model()
    response = model.invoke([system_message] + list(messages))

    return {"messages": [response]}


# Build the graph
builder = StateGraph(MessagesState)

# Add the single model node
builder.add_node("model", model_node)

# Simple flow: START -> model -> END
builder.add_edge(START, "model")
builder.add_edge("model", END)

# Compile the graph
# NOTE: When using LangGraph API (langgraph dev), persistence is handled automatically
# The platform provides checkpointing, so we don't pass a custom checkpointer here
graph = builder.compile()
