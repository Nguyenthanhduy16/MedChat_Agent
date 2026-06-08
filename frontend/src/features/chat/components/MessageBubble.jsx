import { useState } from 'react';
import { Bot, Quote, Copy, Check, ThumbsUp, ThumbsDown, Share, RefreshCw, Volume2, Square } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../../../utils/cn';

export default function MessageBubble({ message, onRetry, onShowSources }) {
  const isUser = message.role === 'user';
  const isError = message.isError;
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  if (!isUser && !message.content && !message.trace_status && !isError) {
    return null;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSpeak = () => {
    if (!('speechSynthesis' in window)) {
      alert('Trình duyệt của bạn không hỗ trợ tính năng đọc văn bản.');
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    } else {
      // Dọn dẹp hàng đợi trước khi đọc mới
      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(message.content);
      utterance.lang = 'vi-VN';
      utterance.rate = 1.0;
      
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      
      setIsSpeaking(true);
      window.speechSynthesis.speak(utterance);
    }
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
        {!isUser && message.trace_status && (() => {
          const isStopped = message.trace_status === 'Đã dừng kết nối.';
          const colorClass = isStopped ? 'text-danger' : 'text-primary';
          const bgClass = isStopped ? 'bg-danger' : 'bg-primary';
          
          return (
            <div className={cn("flex items-center gap-2 mb-2 ml-1 text-xs font-medium", colorClass, !isStopped && "animate-pulse")}>
              <span className="relative flex h-2 w-2">
                {!isStopped && <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", bgClass)}></span>}
                <span className={cn("relative inline-flex rounded-full h-2 w-2", bgClass)}></span>
              </span>
              {message.trace_status}
            </div>
          );
        })()}

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
              {/* Action Buttons (only for assistant) */}
              {!isUser && !isError && (
                <div className="absolute -bottom-9 left-0 opacity-0 group-hover/msg:opacity-100 flex items-center gap-1 z-10">
                  <button
                    onClick={handleCopy}
                    className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover transition-all flex items-center gap-1"
                    title="Sao chép"
                  >
                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover transition-all" title="Tốt">
                    <ThumbsUp className="w-4 h-4" />
                  </button>
                  <button className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover transition-all" title="Chưa tốt">
                    <ThumbsDown className="w-4 h-4" />
                  </button>
                  <button className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover transition-all" title="Chia sẻ">
                    <Share className="w-4 h-4" />
                  </button>
                  <button className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover transition-all" title="Tạo lại" onClick={onRetry}>
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={handleSpeak}
                    className={cn(
                      "p-1.5 rounded-md transition-all",
                      isSpeaking 
                        ? "text-primary bg-primary/10 hover:bg-primary/20" 
                        : "text-text-muted hover:text-text-primary hover:bg-surface-hover"
                    )} 
                    title={isSpeaking ? "Dừng đọc" : "Đọc văn bản"}
                  >
                    {isSpeaking ? <Square className="w-4 h-4 fill-current" /> : <Volume2 className="w-4 h-4" />}
                  </button>
                  {message.sources && message.sources.length > 0 && (
                    <button
                      onClick={() => onShowSources(message.sources)}
                      className="px-2 py-1 rounded-full text-text-muted hover:text-primary hover:bg-primary/5 border border-transparent hover:border-primary/20 transition-all flex items-center gap-1.5"
                      title="Xem nguồn trích dẫn"
                    >
                      <div className="flex items-center justify-center w-[18px] h-[18px] rounded-full bg-blue-100 text-blue-700 text-[9px] font-black tracking-tighter">
                        FR
                      </div>
                      <span className="text-[12px] font-bold">Nguồn</span>
                    </button>
                  )}
                </div>
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
