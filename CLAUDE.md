# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ANNA is an AI assistant app that helps busy parents manage tasks related to their kids (school, education, health, etc.). The primary codebase is a Chrome Extension built with React, TypeScript, and Vite, featuring:
- **Chat Agent** - Conversational AI assistant (Anna) for parenting advice and support
- **Browser Agent** - Browser automation agent for web interactions (available for future use)

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
│   │   ├── shared/             # Types, hooks, components, utilities
│   │   ├── ui/                 # UI component library
│   │   ├── storage/            # Chrome storage API helpers
│   │   ├── i18n/               # Internationalization
│   │   ├── env/                # Environment variables
│   │   └── dev-utils/          # Development utilities
│   └── tests/e2e/              # WebdriverIO E2E tests
├── servers/agents/              # LangGraph agents server (multi-agent support)
│   ├── src/agents/
│   │   ├── chat_agent/         # Conversational assistant agent
│   │   │   ├── agent.py        # Main graph definition
│   │   │   └── prompts/        # System prompt (Anna personality)
│   │   ├── browser_agent/      # Browser automation agent
│   │   │   ├── agent.py        # Main graph definition
│   │   │   ├── nodes/          # Model and tool nodes
│   │   │   ├── tools/          # Browser tool definitions
│   │   │   ├── prompts/        # System prompts
│   │   │   └── state.py        # Agent state types
│   │   └── shared/             # Common utilities
│   ├── langgraph.json          # LangGraph configuration (multi-graph)
│   └── pyproject.toml          # Python dependencies
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

```bash
pnpm i <package> -w                    # Root-level dependency
pnpm i <package> -F <module-name>      # Package-specific (e.g., -F @extension/shared)
```

**IMPORTANT**: Never manually write version numbers in package.json. Always use `pnpm i` commands to install packages - this ensures you get the latest compatible versions and properly updates the lockfile.

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

- Node.js >= 22.15.1 (see `.nvmrc`)
- pnpm 10.11.0 (project uses pnpm workspaces)
- Pre-commit hooks enforce Prettier + ESLint via Husky

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

