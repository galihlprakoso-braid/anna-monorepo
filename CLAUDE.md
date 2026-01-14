# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Guidelines

### **Never Assume Dependency Versions**

**CRITICAL**: When proposing code that uses external dependencies, NEVER assume or hardcode version numbers. Always:
1. Check the actual installed version in `package.json` or `pyproject.toml` first
2. Use the version-appropriate API based on what's actually installed
3. When unsure, consult the repository's documentation in `docs/` directory
4. If proposing new dependencies, recommend installation without specifying versions (e.g., `pnpm add <package>` or `uv add <package>`)

Assuming outdated versions leads to incorrect API usage and broken implementations.

## Project Overview

ANNA is an AI assistant app that helps busy parents manage tasks related to their kids (school, education, health, etc.). The codebase consists of:
- **Chrome Extension** - Built with React, TypeScript, and Vite
  - **Chat Agent** - Conversational AI assistant (Anna) for parenting advice and support
  - **Browser Agent** - Browser automation agent for web interactions (available for future use)
- **Backend Services** - Task management API with database layer
  - **Data Layer** - SQLAlchemy models + Alembic migrations (shared)
  - **API Backend** - FastAPI REST API with Pydantic schemas
  - **API Client** - TypeScript React Query hooks for Chrome extension

## Repository Structure

```
anna-monorepo/
├── clients/chrome-extension/   # Main Chrome Extension (pnpm workspace + Turborepo)
│   ├── chrome-extension/       # Background service worker and manifest
│   │   └── src/background/     # Message handlers for browser automation
│   ├── pages/                  # Extension UI entry points
│   │   ├── side-panel/         # Chat agent UI (primary interface)
│   │   ├── content/            # Content scripts injected into pages
│   │   ├── content-ui/         # React components injected into pages
│   │   └── content-runtime/    # Runtime injectable content scripts
│   ├── packages/               # Shared utilities
│   │   ├── agents/             # AI agent implementations (chat agent, browser agent)
│   │   ├── api/                # API client with React Query hooks (NEW)
│   │   ├── shared/             # Types, hooks, components, utilities
│   │   ├── ui/                 # UI component library
│   │   ├── storage/            # Chrome storage API helpers
│   │   ├── i18n/               # Internationalization
│   │   ├── env/                # Environment variables
│   │   └── dev-utils/          # Development utilities
│   └── tests/e2e/              # WebdriverIO E2E tests
├── servers/
│   ├── agents/                 # LangGraph agents server (multi-agent support)
│   │   ├── src/agents/
│   │   │   ├── chat_agent/     # Conversational assistant agent
│   │   │   │   ├── agent.py    # Main graph definition
│   │   │   │   └── prompts/    # System prompt (Anna personality)
│   │   │   ├── browser_agent/  # Browser automation agent
│   │   │   │   ├── agent.py    # Main graph definition
│   │   │   │   ├── nodes/      # Model and tool nodes
│   │   │   │   ├── tools/      # Browser tool definitions
│   │   │   │   ├── prompts/    # System prompts
│   │   │   │   └── state.py    # Agent state types
│   │   │   └── shared/         # Common utilities
│   │   ├── langgraph.json      # LangGraph configuration (multi-graph)
│   │   └── pyproject.toml      # Python dependencies
│   ├── data/                   # Data layer - SQLAlchemy models + Alembic migrations (NEW)
│   │   ├── src/data/
│   │   │   ├── models/         # SQLAlchemy ORM models
│   │   │   │   └── task.py     # Task model with self-referential hierarchy
│   │   │   ├── core/           # Database configuration
│   │   │   │   ├── base.py     # Base model class
│   │   │   │   └── database.py # Engine, session factory, get_db dependency
│   │   │   └── migrations/     # Alembic migrations
│   │   ├── alembic.ini         # Alembic configuration
│   │   └── pyproject.toml      # Python dependencies
│   └── api/                    # FastAPI backend - Task management API (NEW)
│       ├── src/api/
│       │   ├── core/           # Core configuration
│       │   │   ├── config.py   # Settings (switchable auth/CORS)
│       │   │   └── exceptions.py # Custom exceptions
│       │   ├── task/           # Task feature (cohesion-based)
│       │   │   ├── schemas.py  # Pydantic request/response models
│       │   │   ├── mapper.py   # SQLAlchemy ↔ Pydantic conversion
│       │   │   ├── service.py  # Business logic (CRUD, validation)
│       │   │   └── router.py   # FastAPI endpoints
│       │   └── main.py         # FastAPI application entry point
│       ├── tests/              # Integration tests
│       │   ├── conftest.py     # Pytest fixtures
│       │   └── test_task_api.py # 22 integration tests
│       └── pyproject.toml      # Python dependencies
└── docs/                       # Documentation (langchain docs, MCP library, projects)
```

## Development Commands

All commands run from `clients/chrome-extension/`:

```bash
# Development
pnpm dev                    # Start dev server with HMR (Chrome)
pnpm dev:firefox            # Start dev server (Firefox)

# Building
pnpm build                  # Production build (Chrome)
pnpm build:firefox          # Production build (Firefox)
pnpm zip                    # Build and create distribution ZIP

# Testing
pnpm e2e                    # Run E2E tests (requires build first)

# Code Quality
pnpm lint                   # Run ESLint
pnpm lint:fix               # Fix linting issues
pnpm format                 # Run Prettier
pnpm type-check             # TypeScript type checking

# Utilities
pnpm module-manager         # Enable/disable extension modules
pnpm update-version <ver>   # Update extension version
pnpm clean                  # Clean all build artifacts
```

### Installing Dependencies

#### Frontend (Chrome Extension)

```bash
pnpm i <package> -w                    # Root-level dependency
pnpm i <package> -F <module-name>      # Package-specific (e.g., -F @extension/api)
```

**IMPORTANT**: Never manually write version numbers in package.json. Always use `pnpm i` commands to install packages - this ensures you get the latest compatible versions and properly updates the lockfile.

#### Backend (Python Services)

```bash
cd servers/api  # or servers/data
uv add <package>           # Add dependency (gets latest version)
uv add --dev <package>     # Add dev dependency
uv sync                    # Install all dependencies
```

**IMPORTANT**: Never manually write version numbers in pyproject.toml. Always use `uv add` commands to install packages - this ensures you get the latest compatible versions and properly manages the lockfile.

## Debugging LangGraph Agents

### Fetching Traces from LangSmith

When debugging browser agent or other LangGraph agents, you can fetch full trace data from LangSmith to understand what the model is seeing and deciding.

**Script Location**: `servers/agents/scripts/fetch_trace.py`

#### Prerequisites

```bash
# Ensure langsmith is installed (it should be in pyproject.toml already)
cd servers/agents
uv sync

# Set up environment variables (already in servers/agents/.env)
export LANGSMITH_API_KEY="lsv2_..."  # Your API key
export LANGSMITH_PROJECT="anna-v3"   # Your project name
```

#### Usage

**Fetch a specific trace by ID:**

From a LangSmith trace URL like:
```
https://smith.langchain.com/o/.../projects/p/...?peek=019bbb3d-53f3-7c90-be38-81cee3e18cfd
```

Extract the trace ID (the last part after `peek=`) and run:

```bash
cd servers/agents
python scripts/fetch_trace.py --trace-id 019bbb3d-53f3-7c90-be38-81cee3e18cfd
```

**Fetch the latest trace:**

```bash
python scripts/fetch_trace.py --latest
```

**Fetch from a specific project:**

```bash
python scripts/fetch_trace.py --latest --project-name "browser_agent"
```

**Output to stdout (for piping to other tools):**

```bash
python scripts/fetch_trace.py --trace-id <id> --stdout | jq '.outputs.messages[-1].content'
```

#### Output

By default, traces are saved to `servers/agents/tmp/traces/` with a filename like:
```
trace_<trace-id>_<timestamp>.json
```

The saved JSON includes:
- Full conversation history with all messages
- Complete tool calls and arguments
- Model responses (not truncated)
- Screenshots (base64-encoded images)
- Metadata (timing, costs, etc.)

#### Analyzing Traces

```bash
# View the trace with syntax highlighting
cat tmp/traces/trace_*.json | python -m json.tool | less

# Extract specific information with jq
cat tmp/traces/trace_*.json | jq '.outputs.messages[] | select(.role=="assistant")'

# View just the latest assistant response
cat tmp/traces/trace_*.json | jq '.outputs.messages[-1].content'
```

#### Debugging Workflow

1. **Run the agent** (e.g., trigger browser agent data collection from Chrome extension)
2. **Get the trace URL** from LangSmith UI or copy the trace ID from logs
3. **Fetch the full trace**:
   ```bash
   cd servers/agents
   python scripts/fetch_trace.py --trace-id <id>
   ```
4. **Analyze the trace** to understand:
   - What screenshots/context the model received
   - What tools it decided to call (or not call)
   - What reasoning it provided
   - Where it stopped and why
5. **Iterate on prompts/skills** based on findings
6. **Test again** with a new run

#### Common Issues

- **"LANGSMITH_API_KEY not found"**: Make sure you're running from `servers/agents/` directory where `.env` is located, or export the variable
- **"No traces found"**: Check the project name matches your LangSmith project
- **Truncated images in JSON**: The script preserves full base64-encoded images - they may be very long but are complete

## Architecture

### Extension Entry Points (`pages/`)

| Page | Purpose |
|------|---------|
| `side-panel` | Chrome 114+ side panel (primary interface with chat agent) |
| `content` | Scripts injected into web pages |
| `content-ui` | React components injected into pages |
| `content-runtime` | Runtime injectable content scripts |

### Shared Packages (`packages/`)

- `@extension/agents` - AI agent implementations (chat agent, browser agent)
- `@extension/api` - API client with React Query hooks for Task API (NEW)
- `@extension/shared` - Types, hooks, components, utilities
- `@extension/storage` - Chrome storage API helpers
- `@extension/ui` - UI component library (shadcn/ui compatible)
- `@extension/i18n` - Type-safe internationalization
- `@extension/env` - Environment variable management

### Dependency Flow

Pages → `@extension/agents`, `@extension/ui`, `@extension/i18n` → `@extension/shared`, `@extension/storage` → `chrome-extension` (background)

All internal dependencies use `workspace:*` references.

## Key Patterns

### Environment Variables

- Prefix with `CEB_` in `.env` files
- CLI variables use `CLI_CEB_` prefix
- Access via `process.env['CEB_EXAMPLE']` or import from `@extension/env`

### Manifest Configuration

The extension manifest is defined in TypeScript at `chrome-extension/manifest.ts` and supports both Chrome (Manifest V3) and Firefox.

### Content Scripts

Content scripts are split by target URL pattern:
- `all.iife.js` - Runs on all URLs
- `example.iife.js` - Runs only on specific domains (configure in manifest.ts)

### E2E Testing

Tests use WebdriverIO with Mocha. Test files in `tests/e2e/specs/`:
```bash
pnpm e2e          # Runs all E2E tests after building/zipping
```

## Requirements

### Frontend (Chrome Extension)
- Node.js >= 22.15.1 (see `.nvmrc`)
- pnpm 10.11.0 (project uses pnpm workspaces)
- Pre-commit hooks enforce Prettier + ESLint via Husky

### Backend (Python Services)
- Python >= 3.12 (see `pyproject.toml` in each service)
- uv (fast Python package installer)
- SQLite (development) or PostgreSQL (production)

## AI Agents

The extension includes two LangGraph-powered agents accessible via the LangGraph server:

### Chat Agent (Primary Interface)

The chat agent is a conversational AI assistant named Anna that provides parenting advice and support. It's currently the default interface in the Chrome extension side panel.

#### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Chrome Extension Side Panel (clients/chrome-extension/)         │
│  ┌────────────────────┐         ┌──────────────────────────┐     │
│  │  ChatUI.tsx        │────────▶│  useChatAgent hook       │     │
│  │  (React UI)        │         │  (@extension/agents)     │     │
│  └────────────────────┘         └─────────┬────────────────┘     │
└────────────────────────────────────────────┼──────────────────────┘
                                             │ HTTP streaming
                                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  LangGraph Server (servers/agents/)                              │
│  ┌────────────────┐                                              │
│  │  model_node    │  Simple StateGraph:                          │
│  │  (GPT-4o)      │  START → model_node → END                    │
│  └────────────────┘  Pure conversation (no tools)                │
└──────────────────────────────────────────────────────────────────┘
```

#### Key Files

**Frontend (Chrome Extension)**
| File | Purpose |
|------|---------|
| `packages/agents/lib/chat_agent/hooks/useChatAgent.ts` | LangGraph SDK hook managing server communication |
| `packages/agents/lib/chat_agent/types/index.ts` | TypeScript types for chat messages and state |
| `pages/side-panel/src/components/ChatUI.tsx` | React chat interface using chat agent |

**Backend (LangGraph Server)**
| File | Purpose |
|------|---------|
| `servers/agents/src/agents/chat_agent/agent.py` | Simple StateGraph with single model node |
| `servers/agents/src/agents/chat_agent/prompts/system.prompt.md` | Anna's personality and conversation guidelines |

#### Agent Personality

Anna is designed to be:
- Warm, supportive, and understanding
- Patient and non-judgmental
- Practical and solution-oriented
- Focused on: school, education, children's health, scheduling, parenting advice

#### Configuration

**Backend:**
- **Model**: GPT-4o (OpenAI)
- **Tools**: None (pure conversation)
- **Graph ID**: `chat_agent` (defined in `langgraph.json`)

**Frontend:**
- Uses `useChatAgent` hook from `@extension/agents`
- No screenshot capture or tool execution
- Simple text-based conversation via HTTP streaming

### Browser Automation Agent

The browser automation agent enables web interactions through vision-based understanding and tool execution. Available for future use when browser automation is needed.

#### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Chrome Extension Side Panel (clients/chrome-extension/)         │
│  ┌────────────────────┐         ┌──────────────────────────┐     │
│  │  ChatUI.tsx        │────────▶│  useBrowserAgent hook    │     │
│  │  (React UI)        │         │  (@extension/agents)     │     │
│  └────────────────────┘         └─────────┬────────────────┘     │
└────────────────────────────────────────────┼──────────────────────┘
                                             │ HTTP (interrupt/resume)
                                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  LangGraph Server (servers/agents/)                              │
│  ┌────────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │  model_node    │─────▶│  tool_node   │──────│  Interrupt   │ │
│  │  (GPT-5-mini)  │◀─────│  (Sends      │      │  (Wait for   │ │
│  └────────────────┘      │   interrupt) │      │   client)    │ │
│                          └──────────────┘      └──────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                                             ▲
                                             │ Resume with result
                                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  Chrome Background Script (chrome-extension/src/background/)     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Message Handlers:                                         │  │
│  │  - CAPTURE_SCREENSHOT → Get viewport screenshot           │  │
│  │  - BROWSER_ACTION → Execute tool (click, type, etc.)      │  │
│  │  - TOGGLE_DEBUG_GRID → Show/hide coordinate grid          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          │ chrome.scripting.executeScript        │
│                          ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Content Script Injection (executeBrowserAction)           │  │
│  │  - Runs in web page context                                │  │
│  │  - Performs DOM interactions (click, type, scroll, etc.)   │  │
│  │  - Shows visual feedback (click animations, grid overlay)  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Files

#### Frontend (Chrome Extension)
| File | Purpose |
|------|---------|
| `packages/agents/lib/browser_agent/hooks/useBrowserAgent.ts` | LangGraph SDK hook managing server communication with interrupt/resume |
| `packages/agents/lib/browser_agent/services/chromeMessaging.ts` | Chrome runtime message bridge for screenshots and actions |
| `packages/agents/lib/browser_agent/services/toolExecutor.ts` | Executes tool calls by dispatching to background script |
| `packages/agents/lib/browser_agent/types/serverTypes.ts` | TypeScript types for server communication |
| `packages/agents/lib/browser_agent/types/agentTypes.ts` | Agent message types for UI display |
| `pages/side-panel/src/components/ChatUI.tsx` | React chat interface with message display and input |
| `chrome-extension/src/background/index.ts` | Background service worker with message handlers, sidepanel opener, and content script injection |

#### Backend (LangGraph Server)
| File | Purpose |
|------|---------|
| `servers/agents/src/agents/browser_agent/agent.py` | Main graph definition with model_node → tool_node flow |
| `servers/agents/src/agents/browser_agent/nodes/model_node.py` | LLM reasoning node (GPT-5-mini with tool binding) |
| `servers/agents/src/agents/browser_agent/nodes/tool_node.py` | Tool execution via interrupt/resume pattern |
| `servers/agents/src/agents/browser_agent/tools/browser_tools.py` | Tool schemas (click, type_text, scroll, drag, wait, screenshot) |
| `servers/agents/src/agents/browser_agent/prompts/system.py` | System prompt with grid coordinate instructions |
| `servers/agents/src/agents/browser_agent/state.py` | Agent state types (AgentState, BrowserToolCall, BrowserToolResult) |
| `servers/agents/langgraph.json` | LangGraph server configuration (multi-graph support) |

### Agent Tools

The agent uses a **100x100 grid coordinate system** where (0,0) is top-left and (100,100) is bottom-right. All coordinates are automatically converted to pixel positions based on viewport size.

| Tool | Description | Parameters | Implementation |
|------|-------------|------------|----------------|
| `click` | Click at grid position | `x`, `y` (0-100) | Converts to pixels, dispatches mouse events at coordinates |
| `type_text` | Type text at cursor | `text` | Sets value in focused input or dispatches keyboard events |
| `scroll` | Scroll page | `direction` (up/down/left/right), `amount` (pixels, default: 300) | Calls window.scrollBy() |
| `drag` | Drag between points | `start_x`, `start_y`, `end_x`, `end_y` (0-100) | Dispatches mousedown → mousemove → mouseup events |
| `wait` | Pause execution | `ms` (milliseconds) | JavaScript setTimeout delay |
| `screenshot` | Capture current state | `reason` (optional string) | Uses chrome.tabs.captureVisibleTab() |

### Communication Flow (LangGraph Server Architecture)

1. **User Input**: User types message in ChatUI and clicks Send
2. **Initial Screenshot**: `useBrowserAgent` hook captures viewport screenshot via background script
3. **Server Invocation**: Client sends HTTP request to LangGraph server with:
   - User message (text)
   - Screenshot (base64 PNG data URL)
   - Viewport dimensions
4. **Model Decision**: Server's `model_node` processes request with GPT-5-mini:
   - Analyzes screenshot using vision capabilities
   - Decides on action (tool call) or response (text)
5. **Tool Interrupt**: If tool needed, `tool_node` creates interrupt:
   - Pauses graph execution
   - Sends `BrowserToolCall` to client via HTTP stream
   - Client's `useEffect` detects interrupt
6. **Client Execution**: Client processes interrupt:
   - `executeToolCall()` converts grid coordinates to pixels
   - Sends message to background script via `chrome.runtime.sendMessage`
   - Background script injects and runs `executeBrowserAction()` in page context
   - Action performs DOM manipulation (click, type, scroll, etc.)
   - Shows visual feedback (animations, grid overlay)
7. **Result Capture**: After action completes:
   - Captures new screenshot if requested
   - Gets updated viewport dimensions
   - Creates `BrowserToolResult` with execution outcome
8. **Resume Server**: Client sends result back to server:
   - Uses `thread.submit(undefined, { command: { resume: result } })`
   - Server's `tool_node` receives result and continues
9. **Loop**: Steps 4-8 repeat until task complete (model returns text response instead of tool call)
10. **Streaming**: All messages stream back to UI in real-time via `useStream` hook

### Configuration

#### Backend Server (Python)

```bash
cd servers/agents

# Install dependencies (uses uv for fast installs)
uv sync

# Set OpenAI API key
echo "OPENAI_API_KEY=sk-..." > .env

# Start LangGraph dev server (runs on http://localhost:2024)
langgraph dev
```

- **Model**: GPT-5-mini (configured in `src/agents/browser_agent/nodes/model_node.py`)
- **Python Version**: >=3.12
- **Dependencies**: langchain, langchain-core, langchain-openai, langgraph, langgraph-cli
- **Registered Agents**: `chat_agent`, `browser_agent` (defined in `langgraph.json`)

#### Frontend Extension (TypeScript)

```bash
cd clients/chrome-extension

# Set LangGraph server URL
echo "CEB_LANGGRAPH_API_URL=http://localhost:2024" > .env

# Start development server
pnpm dev
```

- **Framework**: React 19 + TypeScript + Vite
- **SDK**: `@langchain/langgraph-sdk/react` (provides `useStream` hook)
- **Communication**: HTTP streaming with interrupt/resume commands
- **Reconnect**: Automatically resumes threads after page refresh

### Debug Features

- **Grid Overlay**: Toggle 0-100 coordinate grid overlay on the active page
  - Shows grid lines at 10% intervals (0, 10, 20, ... 100)
  - Corner labels indicate coordinate system
  - Access via "Show Grid" button in side panel header
  - Implemented in `background/index.ts → toggleDebugGrid()`

- **Click Animation**: Red pulse animation shows where clicks occur
  - 20px circle with scale animation
  - Helps verify clicks land in correct location
  - Implemented in `background/index.ts → executeBrowserAction()`

- **Console Logging**: Detailed execution logs
  - `[Agent]` prefix for background script logs
  - `[Agent Content]` prefix for injected content script logs
  - `[useBrowserAgent]` prefix for React hook logs
  - Logs include: coordinates, element info, action results, errors

### Development Workflow

#### For Chat Agent (Current Default)

1. Start LangGraph server: `cd servers/agents && langgraph dev`
2. Start extension dev server: `cd clients/chrome-extension && pnpm dev`
3. Load extension in Chrome from `clients/chrome-extension/dist/`
4. Open side panel on any webpage
5. Chat with Anna about parenting, school, health, or scheduling topics

#### For Browser Agent (Future Use)

1. Start LangGraph server: `cd servers/agents && langgraph dev`
2. Start extension dev server: `cd clients/chrome-extension && pnpm dev`
3. Load extension in Chrome from `clients/chrome-extension/dist/`
4. Switch ChatUI to use `useBrowserAgent` instead of `useChatAgent`
5. Open side panel on any webpage
6. Enable grid overlay to visualize coordinate system
7. Enter commands like "Click the search button" or "Scroll down"
8. Watch console logs for detailed execution trace

## Browser Agent - UI Element Detection (NEW)

The browser automation agent now features **automatic UI element detection** powered by OmniParser V2.

### Key Updates

**What Changed:**
- Added `element_detection_node` to agent graph (runs before model_node)
- Upgraded Python requirement: 3.11 → 3.12
- Added OmniParser dependencies (ultralytics, transformers, torch)
- Migrated skills from hardcoded coordinates to semantic descriptions
- Added ~600ms detection overhead per screenshot

**New Repository Structure:**
```
servers/agents/src/agents/browser_agent/
├── nodes/element_detection_node.py  # NEW: UI element detection
├── services/element_detector.py     # NEW: OmniParser wrapper
├── scripts/setup_omniparser.sh      # NEW: Model download script
└── weights/                         # NEW: Model weights (gitignored)
```

### Setup

```bash
cd servers/agents
uv sync                           # Install dependencies
./scripts/setup_omniparser.sh     # Download models (~1GB)
langgraph dev                     # Start server
```

### How It Works

**Detection Pipeline:**
1. Screenshot arrives → `element_detection_node`
2. YOLOv8 detects UI elements (~100ms)
3. Florence generates captions (~500ms)
4. Converts to 0-100 grid coordinates
5. Injects into model prompt:
   ```
   Detected UI Elements:
   - [1] Input "Ask Meta AI or Search" at grid (12, 8)
   - [2] Button "New chat" at grid (5, 5)
   ```
6. Model uses element data for decisions

**Updated Configuration:**
- **Python**: >=3.12
- **New Tools**: `load_skill(skill_name)`
- **Feature Flag**: `ELEMENT_DETECTION_ENABLED=false` to disable
- **Performance**: ~600ms overhead (100ms detection + 500ms captioning)

**Skills System:**
Skills now use semantic descriptions instead of hardcoded coordinates:
- OLD: "Search bar: x=12, y=8"
- NEW: "Search bar: Look for Input with 'Search' caption"

See `prompts/skills/whatsapp-web.skill.prompt.md` for example.

### Testing

```bash
pytest tests/test_element_detection_integration.py -v -s
```

### Documentation

- `ELEMENT_DETECTION_SETUP.md` - Complete setup guide
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- Test with sample image: `tests/images/ss-1.png`

### Updated Backend Files

| File | Status | Purpose |
|------|--------|---------|
| `nodes/element_detection_node.py` | NEW | Preprocesses screenshots |
| `services/element_detector.py` | NEW | OmniParser wrapper |
| `state.py` | UPDATED | Added DetectedElement types |
| `agent.py` | UPDATED | Added detection to graph flow |
| `model_node.py` | UPDATED | Injects detected elements |
| `tool_node.py` | UPDATED | Clears elements on new screenshot |
| `prompts/system.prompt.md` | UPDATED | Element detection docs |
| `prompts/skills/*.skill.prompt.md` | MIGRATED | Semantic descriptions |

---

## Backend Services (NEW)

The ANNA app includes backend services for task management, built with clean architecture and separation of concerns.

### Data Layer (`servers/data`)

Shared data layer that owns database schema and migrations. Can be used by multiple services (API, agents, etc.).

#### Architecture

**Tech Stack:**
- SQLAlchemy 2.0+ (ORM with modern `Mapped[]` syntax)
- Alembic (database migrations)
- SQLite (development) / PostgreSQL (production-ready)

**Key Features:**
- Self-referential Task model (parent-child hierarchy)
- Lazy initialization pattern (singleton engine/session)
- Switchable database backend via `DATABASE_URL` environment variable

#### Key Files

| File | Purpose |
|------|---------|
| `src/data/models/task.py` | SQLAlchemy Task model with enums, relationships, JSON fields |
| `src/data/core/database.py` | Database engine, session factory, `get_db()` dependency |
| `src/data/core/base.py` | Base declarative class for all models |
| `src/data/migrations/` | Alembic migration versions |
| `alembic.ini` | Alembic configuration |

#### Task Model Schema

```python
class TaskModel(Base):
    # Core fields
    id: str (UUID)
    title: str
    description: Optional[str]

    # Status & Priority
    status: TaskStatus (TODO, IN_PROGRESS, COMPLETED, CANCELLED)
    priority: TaskPriority (LOW, MEDIUM, HIGH, URGENT)

    # Timestamps
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime]
    scheduled_date: Optional[datetime]
    completed_at: Optional[datetime]

    # Hierarchy (self-referential)
    parent_task_id: Optional[str]  # Foreign key to tasks.id
    subtasks: relationship to child tasks

    # JSON fields (SQLite-compatible)
    assignees: Optional[list[str]]  # user IDs or "AI"
    recurrence_config: Optional[dict]
    tags: Optional[list[str]]
    extra_data: Optional[dict]  # Extensibility (calendar_event_id, etc.)

    # Owner
    owner_user_id: str  # Hardcoded for now, Firebase auth later
```

#### Database Commands

```bash
cd servers/data

# Install dependencies
uv sync

# Create migration
.venv/bin/alembic revision --autogenerate -m "Description"

# Apply migrations
.venv/bin/alembic upgrade head

# Rollback
.venv/bin/alembic downgrade -1
```

#### Database Configuration

**Switchable backend via environment variable:**
```bash
# SQLite (development)
DATABASE_URL=sqlite:///./data/tasks.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@localhost:5432/tasks
```

For MongoDB, would need to switch from SQLAlchemy to motor/beanie and refactor data layer.

---

### API Backend (`servers/api`)

FastAPI REST API for task management with clean, cohesion-based architecture.

#### Architecture

**Tech Stack:**
- FastAPI 0.128+ (async REST API with OpenAPI docs)
- Pydantic 2.12+ (request/response validation)
- uvicorn (ASGI server with auto-reload)

**Architecture Pattern:**
- **Cohesion-based structure**: Features grouped by domain (`task/`) rather than layers
- **Service layer**: Business logic (CRUD, validation, circular reference prevention)
- **Mapper layer**: Converts SQLAlchemy models ↔ Pydantic schemas
- **Dependency injection**: Uses FastAPI's `Depends()` for database sessions

#### Key Files

| File | Purpose |
|------|---------|
| `src/api/main.py` | FastAPI application with CORS, lifespan, routing |
| `src/api/core/config.py` | Settings (switchable auth/CORS bypass) |
| `src/api/core/exceptions.py` | Custom exceptions (NotFoundError, ValidationError) |
| `src/api/task/schemas.py` | Pydantic models (TaskCreate, TaskUpdate, TaskResponse) |
| `src/api/task/mapper.py` | Converts between SQLAlchemy and Pydantic |
| `src/api/task/service.py` | Business logic (CRUD, hierarchy validation) |
| `src/api/task/router.py` | REST API endpoints |
| `tests/test_task_api.py` | 22 integration tests (all passing) |

#### API Endpoints

**Base URL:** `http://localhost:8000/api/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/tasks/` | Create task |
| `GET` | `/tasks/{id}` | Get task by ID |
| `GET` | `/tasks/` | List tasks with filtering/pagination |
| `PATCH` | `/tasks/{id}` | Update task |
| `DELETE` | `/tasks/{id}` | Delete task (orphan or cascade children) |

**Query Parameters:**
- `parent_id` - Filter by parent ("root" for top-level tasks)
- `status` - Filter by status (todo, in_progress, completed, cancelled)
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 50, max: 100)
- `cascade` - For DELETE: recursively delete children (default: false)

#### Running the API

```bash
cd servers/api

# Install dependencies
uv sync

# Setup environment
cp .env.example .env

# Run server
.venv/bin/python src/api/main.py

# Or with uvicorn directly
.venv/bin/uvicorn api.main:app --reload
```

Visit: http://localhost:8000/docs (Swagger UI auto-documentation)

#### Configuration (Switchable)

**`servers/api/.env`:**
```env
# Security bypass (development)
BYPASS_AUTH=true   # Skip authentication, use DEFAULT_USER_ID
BYPASS_CORS=true   # Allow all origins

# Production: Set both to false
# BYPASS_AUTH=false  # Enable Firebase auth
# BYPASS_CORS=false  # Use strict CORS_ORIGINS list
```

#### Testing

```bash
cd servers/api
.venv/bin/pytest tests/ -v
```

**Coverage:** 22 integration tests covering:
- CRUD operations
- Pagination & filtering
- Task hierarchy (parent/child relationships)
- Circular reference prevention
- Cascade vs orphan deletion
- Validation rules
- Complete workflows

---

### API Client Package (`packages/api`)

TypeScript API client for Chrome extension using Tanstack React Query.

#### Architecture

**Tech Stack:**
- Tanstack React Query 5.0+ (data fetching, caching, mutations)
- TypeScript (manual types matching Pydantic schemas)
- Fetch API (HTTP client)

**Key Features:**
- Type-safe API client
- React Query hooks for queries (useQuery) and mutations (useMutation)
- Automatic cache invalidation
- Optimistic updates
- Error handling

#### Key Files

| File | Purpose |
|------|---------|
| `lib/client.ts` | Base APIClient class with fetch wrapper |
| `lib/task/types.ts` | TypeScript types (Task, TaskCreate, TaskUpdate, etc.) |
| `lib/task/queries.ts` | React Query hooks (useTask, useTasks, useRootTasks, useSubtasks) |
| `lib/task/mutations.ts` | Mutation hooks (useCreateTask, useUpdateTask, useDeleteTask, useToggleTask) |
| `lib/query-client.ts` | React Query client configuration |
| `lib/index.ts` | Package exports |

#### Usage Example

```typescript
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient, useRootTasks, useCreateTask, useToggleTask, TaskStatus } from '@extension/api';

function TaskListContent() {
  // Fetch root tasks
  const { data: tasks, isLoading, error } = useRootTasks();

  // Create task mutation
  const createTask = useCreateTask();

  // Toggle task completion
  const toggleTask = useToggleTask();

  const handleCreateTask = () => {
    createTask.mutate({
      title: 'New Task',
      description: 'Task description',
      priority: TaskPriority.HIGH,
      dueDate: new Date('2026-01-20'),
    });
  };

  const handleToggleTask = (taskId: string) => {
    toggleTask.mutate(taskId);
  };

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="task-list">
      <button onClick={handleCreateTask}>Create Task</button>

      {tasks?.map(task => (
        <div key={task.id}>
          <h3>{task.title}</h3>
          <p>{task.description}</p>
          <span>Status: {task.status}</span>
          <button onClick={() => handleToggleTask(task.id)}>
            {task.status === TaskStatus.COMPLETED ? 'Reopen' : 'Complete'}
          </button>
        </div>
      ))}
    </div>
  );
}

// Wrap with QueryClientProvider
export function TaskList() {
  return (
    <QueryClientProvider client={queryClient}>
      <TaskListContent />
    </QueryClientProvider>
  );
}
```

#### React Query Hooks

**Queries (Data Fetching):**
- `useTask(taskId)` - Fetch single task by ID
- `useTasks(params)` - List tasks with filters (status, parentId, pagination)
- `useRootTasks()` - List top-level tasks (no parent)
- `useSubtasks(parentId)` - List children of a parent task

**Mutations (Data Modification):**
- `useCreateTask()` - Create new task
- `useUpdateTask()` - Update existing task
- `useDeleteTask()` - Delete task (with cascade option)
- `useToggleTask()` - Toggle task completion status

**Query Keys:**
- `taskKeys.all` - All task queries
- `taskKeys.list(filters)` - List queries with specific filters
- `taskKeys.detail(id)` - Single task query

#### Environment Variables

**Chrome Extension `.env`:**
```env
# API URL (optional, defaults to localhost:8000)
VITE_API_URL=http://localhost:8000/api/v1
```

---

### Backend Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Chrome Extension (packages/api)                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  React Query Hooks                                     │  │
│  │  - useRootTasks() → GET /api/v1/tasks?parent_id=root  │  │
│  │  - useCreateTask() → POST /api/v1/tasks/              │  │
│  │  - useUpdateTask() → PATCH /api/v1/tasks/{id}         │  │
│  └──────────────────────┬─────────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────────┘
                          │ HTTP JSON
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI Backend (servers/api)                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Router (task/router.py)                               │  │
│  │  - Validates requests (Pydantic)                       │  │
│  │  - Calls TaskService                                   │  │
│  └──────────────────────┬─────────────────────────────────┘  │
│                         ▼                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Service (task/service.py)                             │  │
│  │  - Business logic (CRUD)                               │  │
│  │  - Validation (circular references, parent exists)     │  │
│  │  - Calls Mapper                                        │  │
│  └──────────────────────┬─────────────────────────────────┘  │
│                         ▼                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Mapper (task/mapper.py)                               │  │
│  │  - Converts Pydantic ↔ SQLAlchemy                      │  │
│  │  - Queries subtask IDs                                 │  │
│  └──────────────────────┬─────────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  Data Layer (servers/data)                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  SQLAlchemy Models (models/task.py)                    │  │
│  │  - TaskModel with self-referential relationship        │  │
│  │  - Enums (TaskStatus, TaskPriority)                    │  │
│  │  - JSON fields (assignees, recurrence_config, etc.)    │  │
│  └──────────────────────┬─────────────────────────────────┘  │
│                         ▼                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Database (core/database.py)                           │  │
│  │  - get_engine() - Lazy engine creation                 │  │
│  │  - get_db() - Session dependency for FastAPI           │  │
│  │  - init_db() - Create all tables                       │  │
│  └──────────────────────┬─────────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │   SQLite DB  │
                  │ tasks.db     │
                  └──────────────┘
```

### Development Workflow

#### 1. Start Data Layer

```bash
cd servers/data
uv sync
.venv/bin/alembic upgrade head  # Apply migrations
```

#### 2. Start API Server

```bash
cd servers/api
uv sync
cp .env.example .env
.venv/bin/python src/api/main.py
```

API runs at: http://localhost:8000
Swagger docs: http://localhost:8000/docs

#### 3. Use in Chrome Extension

Add `@extension/api` to your package dependencies:
```json
{
  "dependencies": {
    "@extension/api": "workspace:*"
  }
}
```

Then use React Query hooks in components:
```typescript
import { useRootTasks, useCreateTask } from '@extension/api';
```

### Data Flow Example

**Creating a task:**

1. **UI**: User clicks "Create Task" → calls `createTask.mutate({ title: "..." })`
2. **React Query**: Sends `POST /api/v1/tasks/` with JSON payload
3. **FastAPI Router**: Validates request via Pydantic `TaskCreate` schema
4. **Service**: Converts to `TaskModel` via mapper, checks parent exists
5. **Data Layer**: Inserts into database via SQLAlchemy
6. **Response**: Returns `TaskResponse` to client
7. **React Query**: Invalidates task list cache, triggers refetch

**Updating task status:**

1. **UI**: User toggles task → calls `toggleTask.mutate(taskId)`
2. **React Query**: Fetches current task, toggles status, sends `PATCH /api/v1/tasks/{id}`
3. **Service**: Validates update, applies changes
4. **React Query**: Updates cache with new task data

### Testing

**API Integration Tests:**
```bash
cd servers/api
.venv/bin/pytest tests/ -v
```

- 22 tests covering all endpoints
- In-memory SQLite (fast, isolated)
- Tests: CRUD, pagination, hierarchy, validation, cascade delete

---

