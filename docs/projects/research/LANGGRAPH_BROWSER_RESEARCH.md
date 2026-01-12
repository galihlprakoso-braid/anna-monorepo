# LangGraph Browser Compatibility Research

## The Problem

When building with Vite for browser (Chrome extension side panel), we get:

```
"AsyncLocalStorage" is not exported by "__vite-browser-external",
imported by "@langchain/langgraph/dist/setup/async_local_storage.js"
```

LangGraph imports `AsyncLocalStorage` from `node:async_hooks` - a **Node.js-only API** unavailable in browsers.

---

## What is `AsyncLocalStorage`?

A Node.js API providing **context that persists across async operations** (like thread-local storage for async code).

**LangGraph uses it for:**
- Thread/conversation isolation (multiple concurrent agent runs)
- Implicit config passing (no need to pass `config` through every function)
- LangSmith tracing (knowing which spans belong to which run)
- `interrupt()` API (human-in-the-loop)
- `task()` functional API

**Browsers don't have it** because they typically handle one user, not multiple concurrent server requests.

---

## Workaround Options

### Option 1: Use `/web` import (0.x versions only)

```typescript
import { StateGraph, END, START } from '@langchain/langgraph/web';
```

**Status**: Stopped working with 1.0.0-alpha.x versions.

### Option 2: Mock AsyncLocalStorage + Vite alias

Create `src/agent/async_hooks.ts`:
```typescript
import { MockAsyncLocalStorage } from '@langchain/core/singletons';
const AsyncLocalStorage = MockAsyncLocalStorage;
export { AsyncLocalStorage };
```

Add to `vite.config.ts`:
```typescript
import path from 'path';

export default defineConfig({
  resolve: {
    alias: {
      'node:async_hooks': path.resolve(__dirname, './src/agent/async_hooks.ts'),
    },
  },
});
```

**Limitations**: Loses tracing, `interrupt()`, and some features. Basic agent execution may work.

### Option 3: Downgrade to 0.x

Use `@langchain/langgraph: ^0.4.9` with `/web` import.

### Option 4: Skip LangGraph entirely

Use `@langchain/openai` directly with manual ReAct loop. Guaranteed browser compatibility.

---

## Relevant GitHub Issues

| Issue | Description |
|-------|-------------|
| [#81](https://github.com/langchain-ai/langgraphjs/issues/81) | Original browser compatibility issue |
| [#869](https://github.com/langchain-ai/langgraphjs/issues/869) | Webpack build error, recommends `/web` import |
| [#879](https://github.com/langchain-ai/langgraphjs/issues/879) | Feature request for web environment support |
| [#1699](https://github.com/langchain-ai/langgraphjs/issues/1699) | 1.x alpha broke `/web` workaround |
| [#974](https://github.com/langchain-ai/langgraphjs/issues/974) | `createSupervisor` doesn't work in browsers |

---

## Official Status

- Browser support is **incomplete** and considered a TODO
- Maintainers acknowledged need for "a separate Pregel class that doesn't use hooks for web"
- No timeline provided for full browser support
- Some features (`createReactAgent`, `interrupt`, functional API) may not work even with workarounds

---

## Resources

- [Running LangChain ReactAgent in browser (dev.to)](https://dev.to/ocleo1/running-langchain-reactagent-in-browser-24ik) - Mock solution for Next.js/webpack
- [LangGraph.js GitHub](https://github.com/langchain-ai/langgraphjs)

---

## Recommendation

For Chrome extension browser context, **Option 4 (skip LangGraph)** is most reliable:
- Use `@langchain/openai` with `ChatOpenAI.bindTools()`
- Implement manual ReAct loop (model calls tool → execute → feed result back)
- Full browser compatibility, no polyfills needed
- Lose some abstractions but gain reliability

If LangGraph features are essential, try **Option 2** (mock + alias) but expect limitations.

---

*Research date: 2025-01-12*
