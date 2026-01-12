# LangGraph Server Migration Plan

> **Update (2026-01-12):** This server has been refactored from `servers/extension_agent/` to `servers/agents/` to support multiple LangGraph agents. The `browser_agent` functionality remains identical.

## Executive Summary

This plan outlines the migration of the ANNA browser automation agent from a client-side LangChain/LangGraph implementation to a **server-side LangGraph architecture** using **interrupts** for bidirectional communication between the Python server and the Chrome extension client.

## Problem Statement

### Current Issue
The current implementation attempts to run LangGraph in the browser (Chrome extension), which fails with:

```
"AsyncLocalStorage" is not exported by "__vite-browser-external",
imported by "@langchain/langgraph/dist/setup/async_local_storage.js"
```

**Root Cause**: LangGraph depends on `AsyncLocalStorage` from `node:async_hooks`, a Node.js-only API unavailable in browsers.

### Why This Matters
- `AsyncLocalStorage` is used for: thread isolation, config passing, tracing, `interrupt()` API, and `task()` API
- Workarounds (mocking, aliasing, downgrading) lose critical features and are unreliable
- Browser compatibility for LangGraph is officially incomplete with no timeline

## Solution Architecture

### Key Insight: Interrupts as a Communication Protocol

The browser automation use case requires **bidirectional communication**: the LLM decides what to do, but the browser must execute it. We leverage LangGraph's **interrupt** mechanism to create a clean request-response pattern:

1. **Server** (Python): Runs LangGraph agent, uses `interrupt()` when browser action needed
2. **Client** (Chrome Extension): Receives interrupt, executes action, resumes with result

```
┌─────────────────────────────────────────────────────────────────────┐
│  Chrome Extension (Client)                                          │
│  ┌────────────────────┐    ┌────────────────────────────────────┐   │
│  │   ChatUI.tsx       │───▶│   useStream hook                   │   │
│  │   (React UI)       │    │   (@langchain/langgraph-sdk/react) │   │
│  └────────────────────┘    └────────────────┬───────────────────┘   │
│                                             │                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Interrupt Handler                                          │     │
│  │  - Receives tool call interrupt                             │     │
│  │  - Executes via Chrome messaging                            │     │
│  │  - Resumes with result                                      │     │
│  └────────────────────────────────┬───────────────────────────┘     │
│                                   │                                 │
│  ┌────────────────────────────────▼───────────────────────────┐     │
│  │  Chrome Messaging (existing)                                │     │
│  │  - captureScreenshot()                                      │     │
│  │  - executeBrowserAction()                                   │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP (streaming)
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LangGraph Server (Python) - servers/extension_agent/              │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Browser Agent Graph                                        │     │
│  │                                                             │     │
│  │  ┌─────────┐     ┌─────────────┐     ┌─────────────┐        │     │
│  │  │  START  │────▶│ model_node  │────▶│ tool_node   │        │     │
│  │  └─────────┘     └──────┬──────┘     └──────┬──────┘        │     │
│  │                         │                   │               │     │
│  │                         │ (tool call)       │ interrupt()   │     │
│  │                         ▼                   │               │     │
│  │                  ┌─────────────┐            │               │     │
│  │                  │    END      │◀───────────┘               │     │
│  │                  └─────────────┘   (when done)              │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Communication Flow (Detailed)

```
1. User: "Click the search button"
   ┌──────────────────────────────────────────────────────────────┐
   │ Client                                                        │
   │ thread.submit({ messages: [...], screenshot: "base64..." })   │
   └────────────────────────────────┬─────────────────────────────┘
                                    ▼
2. Server: Model analyzes screenshot, decides to click
   ┌──────────────────────────────────────────────────────────────┐
   │ Server (model_node)                                           │
   │ AI decides: call click(x=50, y=30)                            │
   │ Returns tool call to tool_node                                │
   └────────────────────────────────┬─────────────────────────────┘
                                    ▼
3. Server: Tool node creates interrupt
   ┌──────────────────────────────────────────────────────────────┐
   │ Server (tool_node)                                            │
   │ result = interrupt({                                          │
   │   "action": "click",                                          │
   │   "args": {"x": 50, "y": 30},                                 │
   │   "request_screenshot": true                                  │
   │ })                                                            │
   └────────────────────────────────┬─────────────────────────────┘
                                    ▼
4. Client: Receives interrupt, executes action
   ┌──────────────────────────────────────────────────────────────┐
   │ Client (interrupt handler)                                    │
   │ if (thread.interrupt) {                                       │
   │   const result = await executeBrowserAction(                  │
   │     interrupt.action, interrupt.args                          │
   │   );                                                          │
   │   const screenshot = await captureScreenshot();               │
   │   thread.submit(undefined, {                                  │
   │     command: { resume: { result, screenshot } }               │
   │   });                                                         │
   │ }                                                             │
   └────────────────────────────────┬─────────────────────────────┘
                                    ▼
5. Server: Continues with result
   ┌──────────────────────────────────────────────────────────────┐
   │ Server (tool_node continues)                                  │
   │ result = interrupt(...) // Returns { result, screenshot }     │
   │ // Feeds result back to model_node                            │
   └────────────────────────────────┬─────────────────────────────┘
                                    ▼
6. Repeat until model returns final answer (no tool call)
```

---

## Implementation Plan

### Phase 1: Server Setup (Python)

**Location**: `servers/extension_agent/`

#### 1.1 Project Structure

```
servers/extension_agent/
├── pyproject.toml              # Python project config
├── langgraph.json              # LangGraph server config
├── .env.example                # Environment variables template
├── src/
│   └── extension_agent/
│       ├── __init__.py
│       ├── agent.py            # Main graph definition
│       ├── state.py            # State schema (TypedDict)
│       ├── nodes/
│       │   ├── __init__.py
│       │   ├── model_node.py   # LLM reasoning node
│       │   └── tool_node.py    # Tool execution with interrupt
│       ├── tools/
│       │   ├── __init__.py
│       │   └── browser_tools.py # Tool definitions (schemas only)
│       └── prompts/
│           ├── __init__.py
│           └── system.py       # System prompt
└── tests/
    └── test_agent.py
```

#### 1.2 State Schema (`state.py`)

```python
from typing import Annotated, Literal, TypedDict
from langgraph.graph.message import add_messages
from langchain.messages import AnyMessage

class BrowserToolCall(TypedDict):
    """Tool call that will be sent to client via interrupt"""
    action: Literal["click", "type", "scroll", "drag", "wait", "screenshot"]
    args: dict
    request_screenshot: bool

class BrowserToolResult(TypedDict):
    """Result returned from client after executing tool"""
    result: str
    screenshot: str | None  # base64 encoded
    viewport: dict | None   # {width, height}

class AgentState(TypedDict):
    """Main agent state"""
    messages: Annotated[list[AnyMessage], add_messages]
    current_screenshot: str | None  # Latest screenshot (base64)
    viewport: dict | None           # Current viewport dimensions
    pending_tool: BrowserToolCall | None  # Tool waiting to be executed
```

#### 1.3 Graph Definition (`agent.py`)

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .state import AgentState
from .nodes import model_node, tool_node

def should_continue(state: AgentState) -> str:
    """Route based on whether model requested a tool call"""
    messages = state["messages"]
    last_message = messages[-1]

    # If AI message has tool calls, go to tool_node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"

    # Otherwise, we're done
    return END

# Build the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("model_node", model_node)
builder.add_node("tool_node", tool_node)

# Add edges
builder.add_edge(START, "model_node")
builder.add_conditional_edges("model_node", should_continue, {
    "tool_node": "tool_node",
    END: END
})
builder.add_edge("tool_node", "model_node")  # Loop back after tool result

# Compile with checkpointer
checkpointer = MemorySaver()  # Use PostgresSaver in production
graph = builder.compile(checkpointer=checkpointer)
```

#### 1.4 Model Node (`nodes/model_node.py`)

```python
from langchain_anthropic import ChatAnthropic
from ..state import AgentState
from ..tools import browser_tools
from ..prompts import SYSTEM_PROMPT

model = ChatAnthropic(model="claude-sonnet-4-5-20250929").bind_tools(browser_tools)

def model_node(state: AgentState) -> dict:
    """LLM reasoning node - decides what action to take"""
    messages = state["messages"]

    # Build message list with system prompt
    system_message = {"role": "system", "content": SYSTEM_PROMPT}

    # Add current screenshot to the last user message if available
    # (handled in message construction)

    response = model.invoke([system_message] + messages)

    return {"messages": [response]}
```

#### 1.5 Tool Node with Interrupt (`nodes/tool_node.py`)

```python
from langgraph.types import interrupt, Command
from ..state import AgentState, BrowserToolCall, BrowserToolResult

def tool_node(state: AgentState) -> dict:
    """
    Tool execution node using interrupt for client-side execution.

    This node:
    1. Extracts tool call from last AI message
    2. Creates interrupt to request client execution
    3. Receives result when client resumes
    4. Returns tool message with result
    """
    messages = state["messages"]
    last_message = messages[-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {}

    tool_call = last_message.tool_calls[0]

    # Create interrupt payload for client
    interrupt_payload: BrowserToolCall = {
        "action": tool_call["name"],
        "args": tool_call["args"],
        "request_screenshot": True  # Always request screenshot after action
    }

    # Pause execution and wait for client to execute the action
    # Client will resume with BrowserToolResult
    result: BrowserToolResult = interrupt(interrupt_payload)

    # Create tool result message
    tool_message = {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": result["result"]
    }

    # Update state with new screenshot if provided
    updates = {"messages": [tool_message]}

    if result.get("screenshot"):
        updates["current_screenshot"] = result["screenshot"]

    if result.get("viewport"):
        updates["viewport"] = result["viewport"]

    return updates
```

#### 1.6 Browser Tools Schema (`tools/browser_tools.py`)

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class ClickArgs(BaseModel):
    """Click at a position using 0-100 grid coordinates"""
    x: int = Field(ge=0, le=100, description="X position (0=left, 50=center, 100=right)")
    y: int = Field(ge=0, le=100, description="Y position (0=top, 50=center, 100=bottom)")

class TypeArgs(BaseModel):
    """Type text at current cursor position"""
    text: str = Field(description="Text to type")

class ScrollArgs(BaseModel):
    """Scroll the page"""
    direction: str = Field(description="Direction: up, down, left, right")
    amount: int = Field(default=300, description="Scroll amount in pixels")

class DragArgs(BaseModel):
    """Drag from one position to another"""
    start_x: int = Field(ge=0, le=100, description="Start X position")
    start_y: int = Field(ge=0, le=100, description="Start Y position")
    end_x: int = Field(ge=0, le=100, description="End X position")
    end_y: int = Field(ge=0, le=100, description="End Y position")

class WaitArgs(BaseModel):
    """Wait for a duration"""
    ms: int = Field(ge=0, le=10000, description="Wait time in milliseconds")

class ScreenshotArgs(BaseModel):
    """Request a new screenshot"""
    reason: str = Field(default="", description="Reason for screenshot")

@tool(args_schema=ClickArgs)
def click(x: int, y: int) -> str:
    """Click at position on screen using grid coordinates (0-100 scale)."""
    pass  # Executed client-side

@tool(args_schema=TypeArgs)
def type_text(text: str) -> str:
    """Type text at current cursor position."""
    pass

@tool(args_schema=ScrollArgs)
def scroll(direction: str, amount: int = 300) -> str:
    """Scroll the page in specified direction."""
    pass

@tool(args_schema=DragArgs)
def drag(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    """Drag from start position to end position."""
    pass

@tool(args_schema=WaitArgs)
def wait(ms: int) -> str:
    """Wait for specified milliseconds."""
    pass

@tool(args_schema=ScreenshotArgs)
def screenshot(reason: str = "") -> str:
    """Request a fresh screenshot of the current page."""
    pass

# Export all tools
browser_tools = [click, type_text, scroll, drag, wait, screenshot]
```

#### 1.7 System Prompt (`prompts/system.py`)

```python
SYSTEM_PROMPT = """You are a browser automation agent that helps users interact with web pages.

## Coordinate System
You operate on a 0-100 grid coordinate system:
- (0, 0) = top-left corner
- (50, 50) = center of viewport
- (100, 100) = bottom-right corner

## Available Tools
- click(x, y): Click at grid position
- type_text(text): Type text at cursor
- scroll(direction, amount): Scroll page (up/down/left/right)
- drag(start_x, start_y, end_x, end_y): Drag between positions
- wait(ms): Wait for specified milliseconds
- screenshot(reason): Request a fresh screenshot

## Guidelines
1. Analyze the screenshot carefully before acting
2. Use precise grid coordinates based on visual analysis
3. After clicking interactive elements, wait briefly for page updates
4. If an action fails, try alternative approaches
5. Explain what you're doing and why

## Response Format
When you've completed the task, provide a clear summary of what was accomplished.
When you need to perform an action, use the appropriate tool.
"""
```

#### 1.8 LangGraph Configuration (`langgraph.json`)

```json
{
  "python_version": "3.11",
  "graphs": {
    "browser_agent": "./src/extension_agent/agent.py:graph"
  },
  "env": ".env"
}
```

#### 1.9 Project Configuration (`pyproject.toml`)

```toml
[project]
name = "extension-agent"
version = "0.1.0"
description = "LangGraph browser automation agent"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2.0",
    "langchain-anthropic>=0.2.0",
    "langchain-core>=0.3.0",
    "langgraph-cli[inmem]>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]
```

---

### Phase 2: Client Refactoring (Chrome Extension)

#### 2.1 Install LangGraph SDK

```bash
cd clients/chrome-extension
pnpm i @langchain/langgraph-sdk -F @extension/sidepanel
```

#### 2.2 New Hook: `useBrowserAgent.ts`

```typescript
// pages/side-panel/src/hooks/useBrowserAgent.ts
import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { useCallback, useEffect, useRef } from "react";
import { captureScreenshot, executeBrowserAction, gridToPixel } from "../agent/services/chromeMessaging";

// Types matching server state
interface BrowserToolCall {
  action: "click" | "type" | "scroll" | "drag" | "wait" | "screenshot";
  args: Record<string, unknown>;
  request_screenshot: boolean;
}

interface BrowserToolResult {
  result: string;
  screenshot: string | null;
  viewport: { width: number; height: number } | null;
}

interface AgentState {
  messages: Message[];
  current_screenshot: string | null;
  viewport: { width: number; height: number } | null;
}

export function useBrowserAgent() {
  const isProcessingInterrupt = useRef(false);

  const thread = useStream<AgentState, { InterruptType: BrowserToolCall }>({
    apiUrl: process.env["CEB_LANGGRAPH_API_URL"] || "http://localhost:2024",
    assistantId: "browser_agent",
    messagesKey: "messages",
  });

  // Handle interrupts (tool execution requests from server)
  useEffect(() => {
    async function handleInterrupt() {
      if (!thread.interrupt || isProcessingInterrupt.current) return;

      isProcessingInterrupt.current = true;
      const toolCall = thread.interrupt.value as BrowserToolCall;

      try {
        // Execute the browser action
        const result = await executeToolCall(toolCall);

        // Capture screenshot if requested
        let screenshot: string | null = null;
        let viewport: { width: number; height: number } | null = null;

        if (toolCall.request_screenshot) {
          const screenshotResult = await captureScreenshot();
          if (screenshotResult) {
            screenshot = screenshotResult.screenshot;
            viewport = screenshotResult.viewport;
          }
        }

        // Resume the graph with the result
        const resumePayload: BrowserToolResult = {
          result,
          screenshot,
          viewport,
        };

        thread.submit(undefined, { command: { resume: resumePayload } });
      } catch (error) {
        // Resume with error
        thread.submit(undefined, {
          command: {
            resume: {
              result: `Error: ${error}`,
              screenshot: null,
              viewport: null,
            },
          },
        });
      } finally {
        isProcessingInterrupt.current = false;
      }
    }

    handleInterrupt();
  }, [thread.interrupt]);

  // Send a message to the agent
  const sendMessage = useCallback(
    async (text: string) => {
      // Capture initial screenshot
      const screenshotResult = await captureScreenshot();
      if (!screenshotResult) {
        console.error("Failed to capture screenshot");
        return;
      }

      const { screenshot, viewport } = screenshotResult;

      // Create user message with screenshot
      const userMessage: Message = {
        type: "human",
        content: [
          { type: "text", text },
          { type: "image_url", image_url: { url: screenshot } },
        ],
      };

      // Submit to server with initial state
      thread.submit({
        messages: [userMessage],
        current_screenshot: screenshot,
        viewport,
      });
    },
    [thread]
  );

  return {
    messages: thread.messages,
    isLoading: thread.isLoading,
    interrupt: thread.interrupt,
    sendMessage,
    stop: thread.stop,
    clear: () => {
      // Note: Clearing requires starting a new thread
      // Could implement by generating new thread ID
    },
  };
}

// Execute tool call based on action type
async function executeToolCall(toolCall: BrowserToolCall): Promise<string> {
  const { action, args } = toolCall;

  switch (action) {
    case "click": {
      const { x, y } = args as { x: number; y: number };
      // Note: Server sends grid coords, client converts to pixels
      // Get current viewport for conversion
      const screenshotResult = await captureScreenshot();
      const viewport = screenshotResult?.viewport || { width: 800, height: 600 };
      const pixel = gridToPixel(x, y, viewport);
      return executeBrowserAction("click", { x: pixel.x, y: pixel.y });
    }

    case "type": {
      const { text } = args as { text: string };
      return executeBrowserAction("type", { text });
    }

    case "scroll": {
      const { direction, amount } = args as { direction: string; amount?: number };
      return executeBrowserAction("scroll", { direction, amount });
    }

    case "drag": {
      const { start_x, start_y, end_x, end_y } = args as {
        start_x: number;
        start_y: number;
        end_x: number;
        end_y: number;
      };
      const screenshotResult = await captureScreenshot();
      const viewport = screenshotResult?.viewport || { width: 800, height: 600 };
      return executeBrowserAction("drag", {
        startX: gridToPixel(start_x, start_y, viewport).x,
        startY: gridToPixel(start_x, start_y, viewport).y,
        endX: gridToPixel(end_x, end_y, viewport).x,
        endY: gridToPixel(end_x, end_y, viewport).y,
      });
    }

    case "wait": {
      const { ms } = args as { ms: number };
      await new Promise((resolve) => setTimeout(resolve, ms));
      return `Waited ${ms}ms`;
    }

    case "screenshot": {
      // Screenshot will be captured after this returns
      return "Screenshot requested";
    }

    default:
      return `Unknown action: ${action}`;
  }
}
```

#### 2.3 Update ChatUI Component

```typescript
// pages/side-panel/src/components/ChatUI.tsx
import { useState, useRef, useEffect } from "react";
import { useBrowserAgent } from "../hooks/useBrowserAgent";
import { toggleDebugGrid } from "../agent/services/chromeMessaging";

// ... MessageBubble and ThinkingIndicator components remain similar

export function ChatUI() {
  const [input, setInput] = useState("");
  const [showGrid, setShowGrid] = useState(false);
  const { messages, isLoading, interrupt, sendMessage, stop } = useBrowserAgent();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ... grid toggle and scroll logic remain similar

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      sendMessage(input.trim());
      setInput("");
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
        <h1 className="text-lg font-semibold text-gray-800">Browser Agent</h1>
        <div className="flex gap-2">
          <button
            onClick={() => toggleDebugGrid(!showGrid).then(() => setShowGrid(!showGrid))}
            className={`text-sm px-2 py-1 rounded ${
              showGrid ? "bg-red-500 text-white" : "bg-gray-200 text-gray-700"
            }`}
          >
            {showGrid ? "Hide Grid" : "Show Grid"}
          </button>
          {isLoading && (
            <button
              onClick={stop}
              className="text-sm px-2 py-1 rounded bg-red-100 text-red-700"
            >
              Stop
            </button>
          )}
        </div>
      </div>

      {/* Show interrupt status */}
      {interrupt && (
        <div className="px-4 py-2 bg-yellow-50 border-b text-sm text-yellow-700">
          Executing: {interrupt.value.action}({JSON.stringify(interrupt.value.args)})
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* ... message rendering ... */}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t bg-gray-50">
        {/* ... input form ... */}
      </form>
    </div>
  );
}
```

#### 2.4 Environment Configuration

Add to `.env`:

```bash
CEB_LANGGRAPH_API_URL=http://localhost:2024
```

#### 2.5 Remove Old Agent Code

After migration, remove:
- `pages/side-panel/src/agent/index.ts` (old agent loop)
- `pages/side-panel/src/agent/middleware/` (no longer needed)
- `pages/side-panel/src/hooks/useAgent.ts` (replaced by useBrowserAgent)

Keep:
- `pages/side-panel/src/agent/services/chromeMessaging.ts` (still needed)
- `pages/side-panel/src/agent/types.ts` (may need updates)
- Background script (unchanged)

---

### Phase 3: Integration and Testing

#### 3.1 Local Development Setup

1. **Start the LangGraph server**:
   ```bash
   cd servers/extension_agent
   pip install -e .
   langgraph dev
   ```
   Server runs at `http://localhost:2024`

2. **Start the Chrome extension**:
   ```bash
   cd clients/chrome-extension
   pnpm dev
   ```

3. **Load the extension** in Chrome and test

#### 3.2 Testing Checklist

- [ ] Server starts without errors
- [ ] Client connects to server
- [ ] User message triggers model response
- [ ] Model tool calls create interrupts
- [ ] Client receives and executes interrupts
- [ ] Client resumes with results
- [ ] Screenshots are captured and sent
- [ ] Full conversation flow works end-to-end
- [ ] Error handling works (network errors, tool failures)

#### 3.3 CORS Configuration

The LangGraph dev server may need CORS configuration. Add to server if needed:

```python
# In agent.py or separate middleware
from fastapi.middleware.cors import CORSMiddleware

# If using custom FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Benefits of This Architecture

1. **No Browser Compatibility Issues**: All LangGraph code runs on the server
2. **Full LangGraph Features**: Interrupts, checkpointing, tracing all work
3. **Clean Separation**: Server handles AI logic, client handles browser actions
4. **Stateful Conversations**: Checkpointer preserves conversation across sessions
5. **Production Ready**: Easy path to deployment (LangSmith, self-hosted)
6. **Debuggable**: LangGraph Studio can visualize and debug the graph

---

## Migration Steps Summary

1. **Create server project** (`servers/extension_agent/`)
2. **Implement state schema** (AgentState, BrowserToolCall, BrowserToolResult)
3. **Implement graph** (model_node, tool_node with interrupt)
4. **Implement tools** (schemas only, execution is client-side)
5. **Install SDK** (`@langchain/langgraph-sdk`) in extension
6. **Create useBrowserAgent hook** (uses useStream, handles interrupts)
7. **Update ChatUI** to use new hook
8. **Configure environment** (API URL)
9. **Test end-to-end**
10. **Clean up old code**

---

## Future Enhancements

1. **Persistent Checkpointing**: Use PostgresSaver for production
2. **Authentication**: Add API key auth between client and server
3. **Multiple Agents**: Support specialized agents (form filling, navigation, etc.)
4. **Caching**: Cache screenshots and tool results
5. **Observability**: Add LangSmith tracing for debugging

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Network latency | Optimize payload size, consider WebSocket |
| Server downtime | Add health checks, retry logic |
| Large screenshots | Compress images, limit resolution |
| CORS issues | Configure server CORS properly |
| State sync | Use thread ID consistently |

---

*Created: 2025-01-12*
*Author: Claude Opus 4.5*
