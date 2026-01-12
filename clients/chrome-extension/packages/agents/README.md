# @extension/agents

AI agent implementations for the Chrome extension.

## Agents

### Browser Agent
LangGraph-powered browser automation agent with interrupt/resume pattern.

**Usage:**
```typescript
import { useBrowserAgent } from '@extension/agents';

const { messages, isRunning, sendMessage, clear } = useBrowserAgent();
```

## Development

```bash
pnpm ready        # Build TypeScript
pnpm type-check   # Check types
pnpm lint         # Lint code
```
