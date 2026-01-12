# LangGraph Server Migration - Implementation Complete

> **Update (2026-01-12):** This server has been refactored from `servers/extension_agent/` to `servers/agents/` to support multiple LangGraph agents. The `browser_agent` functionality remains identical. See the new multi-agent structure in `servers/agents/`.

## Summary

Successfully migrated the ANNA browser automation agent from client-side LangChain to server-side LangGraph using the interrupt pattern for bidirectional communication.

## Implementation Details

### ✅ Phase 1: Backend Setup (Python)
**Location:** `/Users/galihlarasprakoso/Projects/braid/anna-monorepo/servers/extension_agent/`

#### Files Created
- `pyproject.toml` - Project configuration with uv-managed dependencies
- `langgraph.json` - LangGraph server configuration
- `.env.example` - Environment variables template
- `src/extension_agent/state.py` - **Dataclass-based state** (NOT TypedDict)
- `src/extension_agent/models.py` - Pydantic models for tool validation
- `src/extension_agent/nodes/model_node.py` - LLM reasoning node
- `src/extension_agent/nodes/tool_node.py` - Tool execution with interrupts
- `src/extension_agent/tools/browser_tools.py` - Browser tool definitions
- `src/extension_agent/prompts/system.py` - System prompt
- `src/extension_agent/agent.py` - Main graph definition
- `tests/test_*.py` - Comprehensive test suite (40 tests)

#### Dependencies Installed (via uv add)
```bash
langgraph>=1.0.5
langchain-openai>=1.1.7
langchain-core>=1.2.7
langgraph-cli[inmem]>=0.4.11
pytest>=9.0.2 (dev)
pytest-asyncio>=1.3.0 (dev)
```

#### Code Quality Achievements
- ✅ **NO `hasattr()`** - Uses `isinstance()` for type checking
- ✅ **NO `TypedDict`** - Uses `@dataclass` for all state models
- ✅ **Proper typing** - Full type hints throughout
- ✅ **NO hardcoded versions** - All dependencies added via `uv add`
- ✅ **All tests pass** - 40/40 tests passing

---

### ✅ Phase 2: Frontend Refactor (TypeScript)
**Location:** `/Users/galihlarasprakoso/Projects/braid/anna-monorepo/clients/chrome-extension/pages/side-panel/`

#### Files Created
- `src/agent/services/serverTypes.ts` - TypeScript interfaces for server communication
- `src/agent/services/toolExecutor.ts` - Browser action executor with type guards
- `src/hooks/useBrowserAgent.ts` - React hook with `useStream` and interrupt handling

#### Files Modified
- `src/components/ChatUI.tsx` - Updated to use new `useBrowserAgent` hook
- `.env` - Added `CEB_LANGGRAPH_API_URL=http://localhost:2024`

#### Dependencies Installed (via pnpm add)
```bash
@langchain/langgraph-sdk@^1.5.2
```

#### Code Quality Achievements
- ✅ **Proper TypeScript types** - No `any` type usage
- ✅ **Type guards** - Runtime type checking with type predicates
- ✅ **Exhaustive checks** - Switch statements use `never` type
- ✅ **NO hardcoded versions** - Package added via `pnpm add`
- ✅ **Uses `useStream` hook** - Proper SDK integration with interrupt handling

---

## How It Works

### Architecture Flow

```
1. User sends message via ChatUI
   ↓
2. useBrowserAgent captures screenshot and submits to server
   ↓
3. LangGraph server (Python) receives request
   ↓
4. Model node analyzes screenshot, decides action
   ↓
5. If tool call needed: Tool node creates INTERRUPT
   ↓
6. Chrome extension receives interrupt via useStream
   ↓
7. executeToolCall runs browser action locally
   ↓
8. Hook captures new screenshot
   ↓
9. thread.submit({ command: { resume: result } }) resumes server
   ↓
10. Server continues loop until task complete
```

### Key Pattern: Interrupts

The server uses `interrupt()` to pause execution and request client-side actions:

**Python (server):**
```python
# In tool_node.py
interrupt_payload = BrowserToolCall(
    action="click",
    args={"x": 50, "y": 30},
    request_screenshot=True
)
result_dict = interrupt(asdict(interrupt_payload))  # Pauses here!
```

**TypeScript (client):**
```typescript
// In useBrowserAgent.ts
useEffect(() => {
  if (thread.interrupt) {
    const toolCall = thread.interrupt.value as BrowserToolCall;
    const result = await executeToolCall(toolCall.action, toolCall.args);
    const screenshot = await captureScreenshot();
    thread.submit(undefined, {
      command: { resume: { result, screenshot, viewport } }  // Resumes!
    });
  }
}, [thread.interrupt]);
```

---

## Starting the System

### 1. Start LangGraph Server

```bash
cd /Users/galihlarasprakoso/Projects/braid/anna-monorepo/servers/extension_agent

# Create .env file (if not exists)
cp .env.example .env

# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=sk-proj-...

# Start the development server
langgraph dev
```

Server runs at: `http://localhost:2024`

### 2. Start Chrome Extension

```bash
cd /Users/galihlarasprakoso/Projects/braid/anna-monorepo/clients/chrome-extension

# Start development build with HMR
pnpm dev
```

### 3. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `/Users/galihlarasprakoso/Projects/braid/anna-monorepo/clients/chrome-extension/dist`
5. Open the side panel on any web page

---

## Testing Checklist

### Backend Tests
```bash
cd servers/extension_agent
uv run pytest tests/ -v
```
**Result:** ✅ 40/40 tests passing

### Frontend Type Check
```bash
cd clients/chrome-extension
pnpm type-check
```
**Result:** ✅ No errors in new code (pre-existing errors in @extension/ui)

### Integration Test (Manual)
1. ✅ Server starts successfully
2. ⏳ Client connects to server (test after starting both)
3. ⏳ User message triggers model response
4. ⏳ Model tool calls create interrupts
5. ⏳ Client receives and executes interrupts
6. ⏳ Client resumes with results
7. ⏳ Full conversation loop works

---

## Code Quality Verification

### Python Backend
- ✅ NO `hasattr()` function usage (only documentation comments)
- ✅ NO `TypedDict` usage - all `@dataclass`
- ✅ Uses `isinstance()` for type checking
- ✅ Proper Pydantic models for validation
- ✅ NO hardcoded dependency versions
- ✅ Full type hints throughout

### TypeScript Frontend
- ✅ NO `any` type usage
- ✅ Proper type guards with type predicates
- ✅ Exhaustive switch statements with `never` type
- ✅ readonly interfaces for immutability
- ✅ NO hardcoded dependency versions
- ✅ Uses `useStream` hook for interrupt handling

---

## What Was Removed (After Testing)

These files should be removed after confirming the new implementation works:

**Old agent code:**
- `pages/side-panel/src/agent/index.ts`
- `pages/side-panel/src/agent/middleware/summarization.ts`
- `pages/side-panel/src/hooks/useAgent.ts`
- `pages/side-panel/src/agent/tools/*.ts` (all tool files)
- `pages/side-panel/src/agent/context/viewportContext.ts`

**Files kept:**
- `pages/side-panel/src/agent/services/chromeMessaging.ts` ✅ (still needed)
- `pages/side-panel/src/agent/types.ts` ✅ (still needed for UI types)
- `chrome-extension/src/background/` ✅ (unchanged, still needed)

---

## Next Steps

1. ✅ Backend implementation complete
2. ✅ Frontend implementation complete
3. ⏳ **Start both servers and test integration**
4. ⏳ Verify end-to-end flow works
5. ⏳ Remove old code after testing
6. ⏳ Update documentation

---

## Troubleshooting

### Server won't start
- Check `.env` has valid `OPENAI_API_KEY`
- Run `uv sync` to reinstall dependencies
- Check port 2024 isn't already in use

### Client connection fails
- Verify `CEB_LANGGRAPH_API_URL=http://localhost:2024` in client `.env`
- Check server is running and accessible
- Check browser console for CORS errors

### Type errors
- Run `pnpm install` to refresh dependencies
- Check TypeScript version compatibility
- Pre-existing errors in `@extension/ui` can be ignored

---

*Implementation completed: 2026-01-12*
*No hasattr(), no TypedDict, proper types throughout*
