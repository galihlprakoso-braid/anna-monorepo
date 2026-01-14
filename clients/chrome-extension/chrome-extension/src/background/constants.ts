/**
 * Constants for background agent execution
 * Centralizes all configuration to prevent errors
 */

// LangGraph Server Configuration
export const LANGGRAPH_CONFIG = {
  API_URL: process.env['CEB_LANGGRAPH_API_URL'] || 'http://localhost:2024',
  ASSISTANT_ID: 'browser_agent',
  MAX_ITERATIONS: 50, // Safety limit for agent loops
  STREAM_TIMEOUT_MS: 300000, // 5 minutes
  TAB_LOAD_TIMEOUT_MS: 10000, // 10 seconds
  TAB_LOAD_BUFFER_MS: 1000, // Extra wait after load complete
  TAB_ACTIVATION_DELAY_MS: 200, // Delay after tab activation for screenshot
} as const;

// Logging Prefixes
export const LOG_PREFIX = {
  BACKGROUND: '[Background]',
  AGENT: '[Agent]',
  TAB: '[Tab]',
  INTERRUPT: '[Interrupt]',
  ERROR: '[Error]',
  SCREENSHOT: '[Screenshot]',
  TOOL: '[Tool]',
} as const;

// Agent Execution States
export enum AgentExecutionState {
  IDLE = 'idle',
  INITIALIZING = 'initializing',
  RUNNING = 'running',
  INTERRUPTED = 'interrupted',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

// Stream Event Types (from LangGraph SDK)
export const STREAM_EVENT = {
  END: 'end',
  DONE: 'done',
  ERROR: 'error',
} as const;

// Browser Actions (must match server-side definitions)
export const BROWSER_ACTION = {
  CLICK: 'click',
  TYPE: 'type',
  SCROLL: 'scroll',
  DRAG: 'drag',
  WAIT: 'wait',
  SCREENSHOT: 'screenshot',
  COLLECT_DATA: 'collect_data',
} as const;

// Grid to Pixel Conversion
export const GRID_MAX = 100;
