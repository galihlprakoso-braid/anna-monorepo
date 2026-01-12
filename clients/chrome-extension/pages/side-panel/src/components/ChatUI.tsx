import { useState, useRef, useEffect } from 'react';
import { useBrowserAgent } from '../hooks/useBrowserAgent';
import { toggleDebugGrid } from '../agent/services/chromeMessaging';
import type { AgentMessage } from '../agent/types';

function MessageBubble({ message }: { message: AgentMessage }) {
  const roleStyles: Record<string, string> = {
    user: 'bg-blue-500 text-white ml-auto',
    assistant: 'bg-gray-200 text-gray-900',
    thought: 'bg-yellow-100 text-yellow-800 italic text-sm',
    action: 'bg-purple-100 text-purple-800 font-mono text-sm',
    observation: 'bg-green-100 text-green-800 text-sm',
  };

  const roleLabels: Record<string, string> = {
    user: '',
    assistant: '',
    thought: 'Thinking:',
    action: 'Action:',
    observation: 'Result:',
  };

  return (
    <div className={`max-w-[85%] rounded-lg px-4 py-2 ${roleStyles[message.role] || 'bg-gray-100'}`}>
      {roleLabels[message.role] && <div className="text-xs font-semibold mb-1">{roleLabels[message.role]}</div>}
      <div className="whitespace-pre-wrap break-words">{message.content}</div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 text-gray-500">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-sm">Analyzing...</span>
    </div>
  );
}

export function ChatUI() {
  const [input, setInput] = useState('');
  const [showGrid, setShowGrid] = useState(false);
  const { messages, isRunning, sendMessage, clear } = useBrowserAgent();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleToggleGrid = async () => {
    const newState = !showGrid;
    const success = await toggleDebugGrid(newState);
    if (success) {
      setShowGrid(newState);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isRunning) {
      sendMessage(input.trim());
      setInput('');
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
        <h1 className="text-lg font-semibold text-gray-800">Browser Agent</h1>
        <div className="flex gap-2">
          <button
            onClick={handleToggleGrid}
            className={`text-sm px-2 py-1 rounded ${showGrid ? 'bg-red-500 text-white' : 'bg-gray-200 text-gray-700'} hover:opacity-80`}
          >
            {showGrid ? 'Hide Grid' : 'Show Grid'}
          </button>
          <button
            onClick={clear}
            disabled={isRunning}
            className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-8">
            <p className="text-lg mb-2">Tell me what to do on this page</p>
            <p className="text-sm">e.g., "Click the search button" or "Scroll down"</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {isRunning && <ThinkingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t bg-gray-50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="What should I do?"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isRunning}
          />
          <button
            type="submit"
            disabled={isRunning || !input.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isRunning ? '...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
}
