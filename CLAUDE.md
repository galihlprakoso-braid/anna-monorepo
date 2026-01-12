# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ANNA is an AI assistant app that helps busy parents manage tasks related to their kids (school, education, health, etc.). The primary codebase is a Chrome Extension built with React, TypeScript, and Vite, featuring a **browser automation agent** powered by LangChain.

## Repository Structure

```
anna-monorepo/
├── clients/chrome-extension/   # Main Chrome Extension (pnpm workspace + Turborepo)
│   ├── chrome-extension/       # Background service worker and manifest
│   │   └── src/background/     # Message handlers for browser automation
│   ├── pages/                  # Extension UI entry points
│   │   └── side-panel/         # Browser agent UI (primary interface)
│   │       └── src/agent/      # LangChain agent implementation
│   ├── packages/               # Shared utilities (ui, storage, i18n, shared, env, etc.)
│   └── tests/e2e/              # WebdriverIO E2E tests
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
| `popup` | Toolbar popup UI |
| `content` | Scripts injected into web pages |
| `content-ui` | React components injected into pages |
| `content-runtime` | Runtime injectable content scripts |
| `side-panel` | Chrome 114+ side panel |
| `options` | Extension settings page |
| `new-tab` | New Tab override |
| `devtools` / `devtools-panel` | DevTools integration |

### Shared Packages (`packages/`)

- `@extension/shared` - Types, hooks, components, utilities
- `@extension/storage` - Chrome storage API helpers
- `@extension/ui` - UI component library (shadcn/ui compatible)
- `@extension/i18n` - Type-safe internationalization
- `@extension/env` - Environment variable management

### Dependency Flow

Pages → `@extension/ui`, `@extension/i18n` → `@extension/shared`, `@extension/storage` → `chrome-extension` (background)

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

## Browser Automation Agent

The extension includes a LangChain-powered browser automation agent accessible via the Chrome side panel.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Side Panel (pages/side-panel/)                                 │
│  ┌──────────────────┐    ┌─────────────────────────────────┐    │
│  │   ChatUI.tsx     │───▶│   agent/index.ts                │    │
│  │   (React UI)     │    │   (LangChain Agent + Tools)     │    │
│  └──────────────────┘    └───────────────┬─────────────────┘    │
└──────────────────────────────────────────┼──────────────────────┘
                                           │ chrome.runtime.sendMessage
                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Background Script (chrome-extension/src/background/)           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Message Handlers: CAPTURE_SCREENSHOT, BROWSER_ACTION,   │   │
│  │  TOGGLE_DEBUG_GRID                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │ chrome.scripting.executeScript       │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Content Script Injection (executeBrowserAction)         │   │
│  │  Runs in web page context to perform DOM interactions    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `pages/side-panel/src/agent/index.ts` | Main agent loop using LangChain `createAgent` |
| `pages/side-panel/src/agent/prompts.ts` | System prompt with 100x100 grid instructions |
| `pages/side-panel/src/agent/tools/` | Tool definitions (click, type, scroll, drag, wait, screenshot) |
| `pages/side-panel/src/agent/services/chromeMessaging.ts` | Chrome runtime message bridge |
| `pages/side-panel/src/components/ChatUI.tsx` | React chat interface |
| `pages/side-panel/src/hooks/useAgent.ts` | React hook for agent state management |
| `chrome-extension/src/background/index.ts` | Background service worker handling automation messages |

### Agent Tools

The agent uses a **100x100 grid coordinate system** where (0,0) is top-left and (100,100) is bottom-right:

| Tool | Description | Parameters |
|------|-------------|------------|
| `click` | Click at grid position | `x`, `y` (0-100) |
| `type` | Type text at cursor | `text` |
| `scroll` | Scroll page | `direction` (up/down/left/right), `amount` |
| `drag` | Drag between points | `startX`, `startY`, `endX`, `endY` |
| `wait` | Pause execution | `ms` |
| `screenshot` | Capture current state | `reason` (optional) |

### Communication Flow (LangGraph Server Architecture)

1. User sends message via ChatUI
2. `useBrowserAgent` hook captures screenshot and sends to LangGraph server
3. Server (Python) processes with OpenAI GPT-4o model via LangGraph
4. When tool call needed, server sends **interrupt** to client
5. Client executes browser action via background script
6. Client captures new screenshot and **resumes** server with result
7. Server continues loop until task complete
8. Results stream back to UI via `@langchain/langgraph-sdk/react`

### Configuration

- **Backend Server**: `servers/extension_agent/`
  - Model: `gpt-4o` (configured in `model_node.py`)
  - API Key: Set `OPENAI_API_KEY` in `servers/extension_agent/.env`
  - Start with: `langgraph dev`

- **Frontend Extension**: `clients/chrome-extension/`
  - API URL: Set `CEB_LANGGRAPH_API_URL=http://localhost:2024` in `.env`
  - Uses `useStream` hook with interrupt/resume pattern

### Debug Features

- **Grid Overlay**: Toggle 0-100 coordinate grid on page via "Show Grid" button
- **Click Animation**: Red pulse animation shows where clicks occur
- **Console Logging**: Detailed logs prefixed with `[Agent]` or `[Agent Content]`
