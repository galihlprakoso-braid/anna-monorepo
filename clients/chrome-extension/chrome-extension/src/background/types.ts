/**
 * TypeScript interfaces for background agent execution
 */

import type { AgentExecutionState } from './constants';

/**
 * Browser tool call from server interrupt
 * Matches the structure from browser_agent tool_node.py
 */
export interface BrowserToolCall {
  action: string;
  args: Record<string, unknown>;
  request_screenshot: boolean;
}

/**
 * Browser tool result sent back to server when resuming interrupt
 * Matches the expected format from browser_agent tool_node.py
 */
export interface BrowserToolResult {
  result: string;
  screenshot: string | null;
  viewport: { width: number; height: number } | null;
}

/**
 * Screenshot capture result from tab
 */
export interface ScreenshotCapture {
  screenshot: string; // base64 PNG data URL
  viewport: { width: number; height: number };
}

/**
 * Agent execution context
 */
export interface AgentExecutionContext {
  dataSourceId: string;
  tabId: number;
  threadId: string | null;
  state: AgentExecutionState;
  iterationCount: number;
  lastResumeValue?: BrowserToolResult;
}

/**
 * LangGraph message content
 */
export interface MessageContent {
  type: 'text' | 'image_url';
  text?: string;
  image_url?: { url: string };
}

/**
 * LangGraph message format
 */
export interface LangGraphMessage {
  type: 'human' | 'ai' | 'tool';
  content: string | MessageContent[];
}

/**
 * Agent initial state
 */
export interface AgentInitialState extends Record<string, unknown> {
  messages: LangGraphMessage[];
  current_screenshot: string;
  viewport: { width: number; height: number };
}

/**
 * Interrupt value structure from LangGraph
 */
export interface InterruptValue {
  value: BrowserToolCall;
}

/**
 * Stream chunk from LangGraph SDK
 */
export interface StreamChunk {
  event: string;
  data: unknown;
}
