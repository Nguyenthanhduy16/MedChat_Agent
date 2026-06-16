import { useRef, useEffect } from 'react';
import { Bot, User } from 'lucide-react';
import MessageBubble from './MessageBubble';
import AssistantCard from './AssistantCard';
import Composer from './Composer';
import TypingIndicator from './TypingIndicator';
import WelcomeScreen from './WelcomeScreen';
import { useChat } from '../hooks/useChat';

export default function ChatThread({ messages, isLoading, error, sendMessage, onRetry, onRequireAuth }) {
  const scrollRef = useRef(null);

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
      {/* Thread Header */}
      <div className="bg-surface border-b border-border px-6 py-3 flex items-center justify-between shrink-0 z-10">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-text-primary">
              PharmaCare AI Assistant
            </h2>
            <span className="text-[10px] font-bold text-primary bg-primary-soft px-2.5 py-0.5 rounded-full uppercase tracking-wider">
              Active AI Consult
            </span>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Dr. MedAgent is ready to help you
          </p>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-8 h-8 bg-primary-soft rounded-full flex items-center justify-center border-2 border-surface">
            <User className="w-4 h-4 text-primary" />
          </div>
          <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center -ml-2 border-2 border-surface">
            <Bot className="w-4 h-4 text-white" />
          </div>
        </div>
      </div>

      {/* Messages / Welcome Screen */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4 space-y-2 relative"
      >
        {messages.length === 0 ? (
          <WelcomeScreen onSelectSuggestion={sendMessage} />
        ) : (
          <div className="space-y-4 pb-4">
            {messages.map((msg) => {
              if (msg.type === 'card') {
                return (
                  <div key={msg.id} className="flex justify-start pl-11">
                    <AssistantCard card={msg.data} />
                  </div>
                );
              }
              return <MessageBubble key={msg.id} message={msg} onRetry={onRetry} />;
            })}
            
            {/* Loading Indicator */}
            {isLoading && <TypingIndicator />}
          </div>
        )}
      </div>

      {/* Composer */}
      <Composer onSend={sendMessage} disabled={isLoading} onRequireAuth={onRequireAuth} />
    </div>
  );
}
