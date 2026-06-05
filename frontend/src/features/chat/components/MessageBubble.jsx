import { useState } from 'react';
import { Bot, Quote, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../../../utils/cn';

export default function MessageBubble({ message, onRetry }) {
  const isUser = message.role === 'user';
  const isError = message.isError;
  const [copied, setCopied] = useState(false);

  if (!isUser && !message.content && !message.trace_status && !isError) {
    return null;
  }

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
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 overflow-hidden",
          isError ? "bg-danger-soft border border-danger text-danger" : "bg-white border border-border text-primary"
        )}>
          <img src="/logo.png" alt="MedAgent" className="w-full h-full object-cover" />
        </div>
      )}

      <div className={cn('max-w-[85%] space-y-1 group/msg', isUser && 'items-end ml-auto')}>
        {/* Tracing Status */}
        {!isUser && message.trace_status && (
          <div className="flex items-center gap-2 mb-2 ml-1 text-primary text-xs font-medium animate-pulse">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            {message.trace_status}
          </div>
        )}

        {/* Bubble */}
        {(message.content || isError) && (
          <>
            <div
              className={cn(
                'px-4 py-3 text-[15px] leading-relaxed transition-all relative',
                isUser
                  ? 'bg-gray-100 dark:bg-gray-800 text-text-primary rounded-2xl'
                  : isError 
                    ? 'bg-danger-soft border border-danger text-danger rounded-2xl'
                    : 'bg-surface border border-border text-text-primary rounded-2xl shadow-sm'
              )}
            >
              {/* Copy Button (only for assistant) */}
              {!isUser && !isError && (
                <button
                  onClick={handleCopy}
                  className="absolute -bottom-8 left-0 opacity-0 group-hover/msg:opacity-100 p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover transition-all z-10 flex items-center gap-1"
                  title="Sao chép"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
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
                  <p className="whitespace-pre-wrap text-[11px] text-text-secondary leading-relaxed italic">
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
          </>
        )}
      </div>
    </div>
  );
}
