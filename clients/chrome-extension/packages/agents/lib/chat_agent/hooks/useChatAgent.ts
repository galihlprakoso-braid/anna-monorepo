/**
 * React hook for chat agent using LangGraph SDK.
 *
 * Simplified version of useBrowserAgent - no screenshot capture,
 * no interrupt handling, just pure conversation.
 */

import { useStream } from '@langchain/langgraph-sdk/react';
import { useCallback, useState } from 'react';

import type { ChatMessage, ChatAgentState, LangGraphMessage, MessageContent } from '../types/index.js';

const LANGGRAPH_API_URL = process.env['CEB_LANGGRAPH_API_URL'] || 'http://localhost:2024';
const ASSISTANT_ID = 'chat_agent';

/**
 * Extract text content from message
 */
function extractTextContent(content: string | MessageContent[]): string {
  if (typeof content === 'string') {
    return content;
  }

  return content
    .filter((block): block is MessageContent & { type: 'text'; text: string } =>
      block.type === 'text' && typeof block.text === 'string'
    )
    .map(block => block.text)
    .join('');
}

/**
 * Convert server messages to UI display format
 */
function transformMessagesToDisplay(messages: LangGraphMessage[]): ChatMessage[] {
  const result: ChatMessage[] = [];

  for (const msg of messages) {
    const text = extractTextContent(msg.content);
    if (!text) continue;

    if (msg.type === 'human') {
      result.push({ role: 'user', content: text });
    } else if (msg.type === 'ai') {
      result.push({ role: 'assistant', content: text });
    }
  }

  return result;
}

/**
 * Hook for chat agent - simple conversation without browser automation
 */
export function useChatAgent() {
  const [threadId, setThreadId] = useState<string | null>(null);

  const thread = useStream<ChatAgentState>({
    apiUrl: LANGGRAPH_API_URL,
    assistantId: ASSISTANT_ID,
    messagesKey: 'messages',
    threadId,
    onThreadId: setThreadId,
    reconnectOnMount: true,
    onError: (error) => {
      console.error('[useChatAgent] Stream error:', error);
    },
    onFinish: (state) => {
      console.log('[useChatAgent] Stream finished, final state:', state);
    },
  });

  const sendMessage = useCallback(
    (text: string): void => {
      console.log('[useChatAgent] Sending message:', text);

      thread.submit({
        messages: [
          {
            type: 'human',
            content: text,
          },
        ],
      });
    },
    [thread]
  );

  const clear = useCallback((): void => {
    console.log('[useChatAgent] Clearing conversation');
    setThreadId(null);
  }, []);

  const displayMessages = thread.messages
    ? transformMessagesToDisplay(thread.messages as unknown as LangGraphMessage[])
    : [];

  return {
    messages: displayMessages,
    isRunning: thread.isLoading,
    sendMessage,
    clear,
  };
}
