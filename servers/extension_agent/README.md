# Extension Agent

LangGraph browser automation agent for Chrome extension.

## Overview

This server implements a LangGraph-powered browser automation agent that communicates with a Chrome extension client via interrupts. The agent runs on the server, making AI decisions, while browser actions are executed client-side.

## Architecture

```
Server (Python/LangGraph)           Client (Chrome Extension)
        |                                    |
        | --- interrupt(tool_call) --------> |
        |                                    | execute action
        | <-- resume(result, screenshot) --- |
        |                                    |
```

## Development

### Setup

1. Create a `.env` file from the example:
```bash
cp .env.example .env
```

2. Add your OpenAI API key to `.env`:
```bash
OPENAI_API_KEY=your-openai-api-key-here
```

3. Install dependencies:
```bash
uv sync
```

### Running

```bash
# Run server in development mode
langgraph dev

# Run tests
pytest
```

## Project Structure

```
src/extension_agent/
    agent.py           # Main graph definition
    state.py           # State dataclasses
    models.py          # Pydantic models
    nodes/
        model_node.py  # LLM reasoning node
        tool_node.py   # Tool execution with interrupt
    tools/
        browser_tools.py  # Browser tool schemas
    prompts/
        system.py      # System prompt
```
