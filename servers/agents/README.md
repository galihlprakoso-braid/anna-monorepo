# ANNA Agents Server

LangGraph agents server supporting multiple AI agents for the ANNA platform.

## Available Agents

### Browser Agent (`browser_agent`)
Browser automation agent that powers the Chrome extension's AI assistant.

**Features:**
- Screen understanding via vision models
- Browser action execution (click, type, scroll)
- Interrupt-based client-server communication

## Development

### Setup
1. Copy `.env` from template: `cp .env.example .env`
2. Add OpenAI API key: `OPENAI_API_KEY=your-key-here`
3. Install dependencies: `uv sync`

### Running
```bash
langgraph dev        # Start server (all agents)
pytest               # Run all tests
pytest tests/browser_agent/  # Test specific agent
```

## Project Structure
```
src/agents/
    browser_agent/      # Browser automation agent
    shared/            # Shared utilities
    [future_agent]/    # Additional agents
tests/
    browser_agent/     # Agent-specific tests
    shared/            # Shared tests
```

## Adding New Agents

1. Create agent module: `mkdir -p src/agents/new_agent/{nodes,tools,prompts}`
2. Add to `langgraph.json`: `"new_agent": "./src/agents/new_agent/agent.py:graph"`
3. Implement graph in `agent.py` with `graph` export
4. Add tests in `tests/new_agent/`
5. Restart server: `langgraph dev`
