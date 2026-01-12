/**
 * React hook for browser automation agent using LangGraph SDK.
 *
 * This hook uses the useStream hook from @langchain/langgraph-sdk/react
 * to communicate with the LangGraph server and handles interrupts for
 * client-side tool execution.
 */

import { useStream } from '@langchain/langgraph-sdk/react';
import { useCallback, useEffect, useRef, useState } from 'react';

import type { AgentMessage } from '../types/index.js';
import type { BrowserToolCall } from '../types/index.js';
import { captureScreenshot } from '../services/index.js';
import { executeToolCall } from '../services/index.js';

const LANGGRAPH_API_URL = process.env['CEB_LANGGRAPH_API_URL'] || 'http://localhost:2024';
const ASSISTANT_ID = 'browser_agent';

/**
 * Message content type from LangGraph SDK
 */
interface MessageContent {
  type: 'text' | 'image_url';
  text?: string;
  image_url?: { url: string };
}

/**
 * Message type from LangGraph SDK
 */
interface LangGraphMessage {
  type: 'human' | 'ai' | 'tool';
  content: string | MessageContent[];
  tool_calls?: Array<{ name: string; args: Record<string, unknown>; id: string }>;
}

/**
 * Agent state shape from server
 */
interface AgentState {
  messages: LangGraphMessage[];
  current_screenshot: string | null;
  viewport: { width: number; height: number } | null;
}

/**
 * Tool result sent back to server when resuming interrupt
 */
interface BrowserToolResult {
  result: string;
  screenshot: string | null;
  viewport: { width: number; height: number } | null;
}

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
function transformMessagesToDisplay(messages: LangGraphMessage[]): AgentMessage[] {
  const result: AgentMessage[] = [];

  for (const msg of messages) {
    if (msg.type === 'human') {
      const text = extractTextContent(msg.content);
      if (text) {
        result.push({ role: 'user', content: text });
      }
    } else if (msg.type === 'ai') {
      // Check for tool calls first
      if (msg.tool_calls && msg.tool_calls.length > 0) {
        for (const toolCall of msg.tool_calls) {
          result.push({
            role: 'action',
            content: `${toolCall.name}(${JSON.stringify(toolCall.args)})`,
          });
        }
      } else {
        // Regular AI text response
        const text = extractTextContent(msg.content);
        if (text) {
          result.push({ role: 'assistant', content: text });
        }
      }
    } else if (msg.type === 'tool') {
      const text = extractTextContent(msg.content);
      if (text) {
        result.push({ role: 'observation', content: text });
      }
    }
  }

  return result;
}

/**
 * Hook for browser automation agent with interrupt handling
 */
export function useBrowserAgent() {
  // Track whether we're currently processing an interrupt
  const isProcessingInterrupt = useRef(false);

  // Thread ID for conversation persistence and resumption
  const [threadId, setThreadId] = useState<string | null>(null);

  // Use LangGraph SDK's useStream hook for bidirectional communication
  const thread = useStream<AgentState, { InterruptType: BrowserToolCall }>({
    apiUrl: LANGGRAPH_API_URL,
    assistantId: ASSISTANT_ID,
    messagesKey: 'messages',
    threadId,
    onThreadId: setThreadId,
    reconnectOnMount: true, // Auto-resume after page refresh
    onError: (error) => {
      console.error('[useBrowserAgent] Stream error:', error);
    },
    onFinish: (state) => {
      console.log('[useBrowserAgent] Stream finished, final state:', state);
    },
  });

  // Handle interrupts (tool execution requests from server)
  useEffect(() => {
    async function handleInterrupt(): Promise<void> {
      // Skip if no interrupt or already processing
      if (!thread.interrupt || isProcessingInterrupt.current) {
        return;
      }

      isProcessingInterrupt.current = true;

      const toolCall = thread.interrupt.value as BrowserToolCall;
      console.log('[useBrowserAgent] Received interrupt:', toolCall);

      try {
        // Execute the tool call locally
        const result = await executeToolCall(
          toolCall.action,
          toolCall.args,
          toolCall.request_screenshot
        );

        // Capture screenshot if requested
        let screenshot: string | null = null;
        let viewport: { width: number; height: number } | null = null;

        if (toolCall.request_screenshot) {
          const screenshotResult = await captureScreenshot();
          if (screenshotResult) {
            screenshot = screenshotResult.screenshot;
            viewport = screenshotResult.viewport;
          }
        }

        // Construct the result to send back
        const toolResult: BrowserToolResult = {
          result,
          screenshot,
          viewport,
        };

        console.log('[useBrowserAgent] Resuming with result:', result);

        // Resume the graph with the result
        // The SDK expects Command({ resume: ... })
        thread.submit(undefined, {
          command: { resume: toolResult },
        });
      } catch (error) {
        console.error('[useBrowserAgent] Interrupt handler error:', error);

        // Resume with error result
        const errorResult: BrowserToolResult = {
          result: `Error: ${error instanceof Error ? error.message : String(error)}`,
          screenshot: null,
          viewport: null,
        };

        thread.submit(undefined, {
          command: { resume: errorResult },
        });
      } finally {
        isProcessingInterrupt.current = false;
      }
    }

    void handleInterrupt();
  }, [thread.interrupt, thread]);

  // Send a new message to the agent
  const sendMessage = useCallback(
    async (text: string): Promise<void> => {
      // Capture initial screenshot
      const screenshotResult = await captureScreenshot();

      if (!screenshotResult) {
        console.error('[useBrowserAgent] Failed to capture initial screenshot');
        return;
      }

      const { screenshot, viewport } = screenshotResult;

      // Build user message with screenshot
      const messageContent: MessageContent[] = [
        { type: 'text', text },
        { type: 'image_url', image_url: { url: screenshot } },
      ];

      console.log('[useBrowserAgent] Sending message with screenshot');

      // Submit to server with initial state
      thread.submit({
        messages: [
          {
            type: 'human',
            content: messageContent,
          },
        ],
        current_screenshot: screenshot,
        viewport,
      });
    },
    [thread]
  );

  // Clear conversation (starts new thread)
  const clear = useCallback((): void => {
    console.log('[useBrowserAgent] Clearing conversation');
    // Reset thread ID to start a fresh conversation
    setThreadId(null);
  }, []);

  // Transform server messages to display format
  const displayMessages = thread.messages ? transformMessagesToDisplay(thread.messages as unknown as LangGraphMessage[]) : [];

  return {
    messages: displayMessages,
    isRunning: thread.isLoading,
    sendMessage,
    clear,
  };
}
