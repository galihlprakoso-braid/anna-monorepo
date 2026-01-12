"""Tests for the browser automation agent graph."""

from langchain_core.messages import AIMessage, HumanMessage

from extension_agent.agent import create_graph, should_continue
from extension_agent.state import AgentState


class TestShouldContinue:
    """Tests for the should_continue routing function."""

    def test_empty_messages_returns_end(self):
        """Test that empty messages returns END."""
        state = AgentState(messages=[])
        result = should_continue(state)
        assert result == "__end__"

    def test_human_message_returns_end(self):
        """Test that human message without AI response returns END."""
        state = AgentState(messages=[HumanMessage(content="Hello")])
        result = should_continue(state)
        assert result == "__end__"

    def test_ai_message_without_tool_calls_returns_end(self):
        """Test that AI message without tool calls returns END."""
        state = AgentState(
            messages=[
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
            ]
        )
        result = should_continue(state)
        assert result == "__end__"

    def test_ai_message_with_tool_calls_returns_tool_node(self):
        """Test that AI message with tool calls returns tool_node."""
        state = AgentState(
            messages=[
                HumanMessage(content="Click the button"),
                AIMessage(
                    content="I'll click the button",
                    tool_calls=[
                        {
                            "id": "call_123",
                            "name": "click",
                            "args": {"x": 50, "y": 50},
                        }
                    ],
                ),
            ]
        )
        result = should_continue(state)
        assert result == "tool_node"

    def test_ai_message_with_empty_tool_calls_returns_end(self):
        """Test that AI message with empty tool_calls list returns END."""
        state = AgentState(
            messages=[
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!", tool_calls=[]),
            ]
        )
        result = should_continue(state)
        assert result == "__end__"


class TestCreateGraph:
    """Tests for the graph creation."""

    def test_graph_creation(self):
        """Test that the graph can be created."""
        builder = create_graph()
        assert builder is not None

    def test_graph_has_model_node(self):
        """Test that the graph has the model_node."""
        builder = create_graph()
        assert "model_node" in builder.nodes

    def test_graph_has_tool_node(self):
        """Test that the graph has the tool_node."""
        builder = create_graph()
        assert "tool_node" in builder.nodes

    def test_graph_compiles(self):
        """Test that the graph compiles without errors."""
        from langgraph.checkpoint.memory import MemorySaver

        builder = create_graph()
        checkpointer = MemorySaver()
        compiled = builder.compile(checkpointer=checkpointer)
        assert compiled is not None
