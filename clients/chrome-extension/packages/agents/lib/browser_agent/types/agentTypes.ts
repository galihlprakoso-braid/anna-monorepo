export interface AgentMessage {
  role: 'user' | 'assistant' | 'thought' | 'action' | 'observation';
  content: string;
}

// Agent event types emitted during streaming
export const AgentEventType = {
  THOUGHT: 'thought',
  ACTION: 'action',
  OBSERVATION: 'observation',
  ANSWER: 'answer',
  ERROR: 'error',
} as const;

export type AgentEventTypeValue = (typeof AgentEventType)[keyof typeof AgentEventType];

export interface AgentEvent {
  type: AgentEventTypeValue;
  content: string;
}

// LangChain stream step names
export const StreamStep = {
  MODEL: 'model',
  TOOLS: 'tools',
  INTERRUPT: '__interrupt__',
} as const;

export type StreamStepValue = (typeof StreamStep)[keyof typeof StreamStep];

// LangChain message types from stream
export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  id?: string;
}

export interface TextContentBlock {
  type: 'text';
  text: string;
}

export type MessageContent = string | Array<TextContentBlock | { type: string; text?: string }>;

export interface StreamMessage {
  tool_calls?: ToolCall[];
  content?: MessageContent;
  name?: string;
}

export interface StreamStepData {
  messages?: StreamMessage[];
}

export type StreamChunk = Record<string, StreamStepData>;
