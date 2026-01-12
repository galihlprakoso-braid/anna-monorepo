"""Main LangGraph agent definition for browser automation.

This module defines the browser automation agent graph that:
1. Takes user messages with screenshots
2. Uses an LLM to decide what browser action to take
3. Pauses (via interrupt) for the client to execute the action
4. Resumes with the result and continues until done
"""

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from extension_agent.nodes.model_node import model_node
from extension_agent.nodes.tool_node import tool_node
from extension_agent.state import AgentState


def should_continue(state: AgentState) -> str:
    """Route based on whether model requested a tool call.

    Uses isinstance() for type checking instead of hasattr().

    Args:
        state: Current agent state

    Returns:
        "tool_node" if there's a tool call to execute, END otherwise
    """
    messages = state.messages

    if not messages:
        return END

    last_message = messages[-1]

    # Use isinstance() for type checking - NOT hasattr()
    if isinstance(last_message, AIMessage):
        # AIMessage always has tool_calls attribute (list, possibly empty)
        if last_message.tool_calls:
            return "tool_node"

    # No tool call - we're done
    return END


def create_graph() -> StateGraph:
    """Create the browser automation agent graph.

    Returns:
        StateGraph builder (checkpointing handled by LangGraph API server)
    """
    # Build the graph
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("model_node", model_node)
    builder.add_node("tool_node", tool_node)

    # Add edges
    builder.add_edge(START, "model_node")
    builder.add_conditional_edges(
        "model_node",
        should_continue,
        {
            "tool_node": "tool_node",
            END: END,
        },
    )
    # Loop back after tool result to let model decide next action
    builder.add_edge("tool_node", "model_node")

    return builder


# Compile the graph
# NOTE: When using LangGraph API (langgraph dev), persistence is handled automatically
# The platform provides checkpointing, so we don't pass a custom checkpointer here
graph = create_graph().compile()
