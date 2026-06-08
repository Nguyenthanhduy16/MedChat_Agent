import { useRef, useEffect } from 'react';
import { Bot, User } from 'lucide-react';
import MessageBubble from './MessageBubble';
import AssistantCard from './AssistantCard';
import Composer from './Composer';
import TypingIndicator from './TypingIndicator';
import WelcomeScreen from './WelcomeScreen';
import { useChat } from '../hooks/useChat';
import { hasActiveAssistantTrace } from '../utils/messageState';

export default function ChatThread({ messages, isLoading, error, sendMessage, stopMessage, onRetry, onRequireAuth, onShowSources }) {
  const scrollRef = useRef(null);
  const hasTraceStatus = hasActiveAssistantTrace(messages);

  // Auto-scroll to bottom whenever messages or loading state changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full bg-surface-muted">
      {/* Messages / Welcome Screen */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-8 space-y-2 relative"
      >
        {messages.length === 0 ? (
          <WelcomeScreen onSelectSuggestion={sendMessage} />
        ) : (
          <div className="space-y-6 pb-32 max-w-3xl mx-auto w-full">
            {messages.map((msg) => {
              if (msg.type === 'card') {
                return (
                  <div key={msg.id} className="flex justify-start">
                    <AssistantCard card={msg.data} />
                  </div>
                );
              }
              return <MessageBubble key={msg.id} message={msg} onRetry={onRetry} onShowSources={onShowSources} />;
            })}
            
            {/* Loading Indicator */}
            {isLoading && !hasTraceStatus && <TypingIndicator />}
          </div>
        )}
      </div>

      {/* Composer */}
      <Composer onSend={sendMessage} onStop={stopMessage} disabled={isLoading} onRequireAuth={onRequireAuth} />
    </div>
  );
}
