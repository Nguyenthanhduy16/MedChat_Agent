import { useState } from 'react';
import { Bot, Quote, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../../../utils/cn';

export default function MessageBubble({ message, onRetry }) {
  const isUser = message.role === 'user';
  const isError = message.isError;
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        'flex gap-3 animate-fade-in mb-4 group',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {/* Bot Avatar */}
      {!isUser && (
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 shadow-sm border",
          isError ? "bg-danger-soft border-danger text-danger" : "bg-surface-muted border-border text-primary"
        )}>
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div className={cn('max-w-[80%] space-y-1', isUser && 'items-end')}>
        {/* Bubble */}
        <div
          className={cn(
            'px-4 py-3 text-sm leading-relaxed shadow-sm transition-all relative',
            isUser
              ? 'bg-primary text-white rounded-2xl rounded-br-md'
              : isError 
                ? 'bg-danger-soft border border-danger text-danger rounded-2xl rounded-bl-md'
                : 'bg-surface border border-border text-text-primary rounded-2xl rounded-bl-md'
          )}
        >
          {/* Copy Button (only for assistant) */}
          {!isUser && !isError && (
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1.5 bg-surface border border-border rounded-lg text-text-muted hover:text-primary hover:border-primary transition-all shadow-sm z-10"
              title="Sao chép"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          )}

          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : isError ? (
            <div className="flex flex-col gap-2">
              <p className="font-medium">{message.content}</p>
              <button 
                onClick={onRetry}
                className="w-fit text-[11px] font-bold uppercase tracking-wider bg-danger text-white px-3 py-1.5 rounded-lg hover:bg-danger/90 transition-colors shadow-sm"
              >
                Thử lại
              </button>
            </div>
          ) : (
            <div className="markdown-body prose prose-sm max-w-none prose-slate dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Chart Image */}
          {!isUser && !isError && message.image && (
            <div className="mt-3 overflow-hidden rounded-lg border border-border bg-surface p-1">
              <img
                src={message.image}
                alt="MedAgent Chart"
                className="w-full h-auto object-contain"
                loading="lazy"
              />
            </div>
          )}

          {/* Sources Section */}
          {!isUser && message.sources && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <div className="flex items-center gap-1.5 mb-1 text-[10px] font-bold text-text-muted uppercase tracking-wider">
                <Quote className="w-3 h-3" />
                Nguồn trích dẫn
              </div>
              <p className="text-[11px] text-text-secondary leading-relaxed italic">
                {message.sources}
              </p>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <p
          className={cn(
            'text-[10px] text-text-muted px-1 mt-1 font-medium',
            isUser ? 'text-right' : 'text-left'
          )}
        >
          {message.timestamp}
        </p>
      </div>
    </div>
  );
}
