/**
 * Chat agent type definitions.
 * Simplified from browser_agent - no tool types needed.
 */

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

/**
 * Message content type from LangGraph SDK
 */
export interface MessageContent {
  type: 'text';
  text: string;
}

/**
 * Message type from LangGraph SDK
 */
export interface LangGraphMessage {
  type: 'human' | 'ai';
  content: string | MessageContent[];
}

/**
 * Agent state shape from server
 */
export interface ChatAgentState {
  messages: LangGraphMessage[];
}
