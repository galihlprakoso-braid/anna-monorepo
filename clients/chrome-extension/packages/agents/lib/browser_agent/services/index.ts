// Re-export service functions
export {
  captureScreenshot,
  executeBrowserAction,
  toggleDebugGrid,
  gridToPixel,
  type Viewport,
  type ScreenshotResult
} from './chromeMessaging.js';

export { executeToolCall } from './toolExecutor.js';
