// Browser Agent Public API

// Hook
export { useBrowserAgent } from './hooks/useBrowserAgent.js';

// Services (for utilities like grid toggle)
export {
  captureScreenshot,
  executeBrowserAction,
  toggleDebugGrid,
  type Viewport,
  type ScreenshotResult
} from './services/index.js';

// Types
export type {
  AgentMessage,
  BrowserToolCall,
  BrowserAction,
  BrowserToolArgs,
  ClickArgs,
  TypeArgs,
  ScrollArgs,
  DragArgs,
  WaitArgs,
  ScreenshotArgs
} from './types/index.js';
