import { useState, useRef, useEffect } from 'react';
import { Send, Monitor, Paperclip, Mic } from 'lucide-react';

export default function Composer({ onSend, disabled, onRequireAuth }) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [message]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim() || disabled) return;
    if (onRequireAuth) { onRequireAuth(); return; }
    onSend?.(message.trim());
    setMessage('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-white via-white to-transparent pointer-events-none z-20">
      <div className="max-w-3xl mx-auto w-full pointer-events-auto">
        <form 
          onSubmit={handleSubmit} 
          className="relative flex items-end bg-surface border border-border shadow-sm rounded-[24px] px-2 py-2 transition-shadow focus-within:shadow-md focus-within:border-primary/30"
        >
          {/* Left Actions */}
          <button
            type="button"
            className="w-9 h-9 flex items-center justify-center rounded-full text-text-muted hover:bg-surface-hover hover:text-text-primary transition-colors shrink-0"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          {/* Input */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={disabled ? "MedAgent đang xử lý..." : "Hỏi về triệu chứng, thuốc hoặc vấn đề sức khỏe..."}
            className="flex-1 bg-transparent px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none disabled:opacity-50 min-w-0 resize-none overflow-y-auto"
            style={{ maxHeight: '200px' }}
          />

          {/* Right Actions */}
          <div className="flex items-center gap-1 pr-1 shrink-0">
            <button
              type="button"
              className="w-9 h-9 hidden sm:flex items-center justify-center rounded-full text-text-muted hover:bg-surface-hover hover:text-text-primary transition-colors"
            >
              <Mic className="w-5 h-5" />
            </button>
            <button
              type="submit"
              disabled={!message.trim() || disabled}
              className="w-9 h-9 flex items-center justify-center rounded-full transition-all disabled:opacity-50 disabled:bg-surface-muted disabled:text-text-muted bg-primary text-white hover:bg-primary-dark"
            >
              <Send className="w-4 h-4 ml-0.5" />
            </button>
          </div>
        </form>

        {/* Disclaimer */}
        <div className="text-center mt-2">
          <p className="text-[11px] text-text-muted">
            AI có thể mắc lỗi. Vui lòng tham khảo ý kiến bác sĩ hoặc chuyên gia y tế trước khi áp dụng.
          </p>
        </div>
      </div>
    </div>
  );
}
