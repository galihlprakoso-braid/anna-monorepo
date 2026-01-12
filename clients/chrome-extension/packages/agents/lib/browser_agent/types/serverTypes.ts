/**
 * TypeScript interfaces for LangGraph Server API response types
 * Based on official LangGraph SDK documentation
 */

export type BrowserAction = 'click' | 'type' | 'scroll' | 'drag' | 'wait' | 'screenshot';

export interface ClickArgs {
  readonly x: number;
  readonly y: number;
}

export interface TypeArgs {
  readonly text: string;
}

export interface ScrollArgs {
  readonly direction: 'up' | 'down' | 'left' | 'right';
  readonly amount: number;
}

export interface DragArgs {
  readonly start_x: number;
  readonly start_y: number;
  readonly end_x: number;
  readonly end_y: number;
}

export interface WaitArgs {
  readonly ms: number;
}

export interface ScreenshotArgs {
  readonly reason?: string;
}

export type BrowserToolArgs = ClickArgs | TypeArgs | ScrollArgs | DragArgs | WaitArgs | ScreenshotArgs;

export interface BrowserToolCall {
  readonly action: BrowserAction;
  readonly args: BrowserToolArgs;
  readonly request_screenshot: boolean;
}

export interface ServerToolCall {
  readonly name: string;
  readonly args: BrowserToolCall;
  readonly id: string;
  readonly type: 'tool_call';
}

export interface ServerTextBlock {
  readonly type: 'text';
  readonly text: string;
}

export type ServerContentBlock = ServerTextBlock | { readonly type: string; readonly text?: string };

export interface ServerAIMessage {
  readonly type: 'ai';
  readonly content: string | readonly ServerContentBlock[];
  readonly tool_calls?: readonly ServerToolCall[];
}

export interface ServerToolMessage {
  readonly type: 'tool';
  readonly content: string;
  readonly tool_call_id: string;
}

export type ServerMessage = ServerAIMessage | ServerToolMessage;

export interface ServerStreamChunk {
  readonly agent?: {
    readonly messages: readonly ServerMessage[];
  };
  readonly tools?: {
    readonly messages: readonly ServerMessage[];
  };
}

export interface ServerRunResult {
  readonly success: boolean;
  readonly error?: string;
  readonly final_answer?: string;
}
