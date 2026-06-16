import { useState } from 'react';
import { Send, Monitor, Paperclip, Mic } from 'lucide-react';

export default function Composer({ onSend, disabled, onRequireAuth }) {
  const [message, setMessage] = useState('');

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
    <div className="border-t border-border bg-surface p-4 relative z-20">
      {/* Mode indicator */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex items-center gap-1.5">
          <button className="w-7 h-7 flex items-center justify-center rounded-md text-text-muted hover:text-text-secondary hover:bg-surface-hover transition-colors">
            <Monitor className="w-4 h-4" />
          </button>
          <button className="w-7 h-7 flex items-center justify-center rounded-md text-text-muted hover:text-text-secondary hover:bg-surface-hover transition-colors">
            <Paperclip className="w-4 h-4" />
          </button>
          <button className="w-7 h-7 flex items-center justify-center rounded-md text-text-muted hover:text-text-secondary hover:bg-surface-hover transition-colors">
            <Mic className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-success rounded-full animate-pulse"></span>
          <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider">
            Medical Mode Active
          </span>
        </div>
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="flex items-end gap-3">
        <div className="flex-1 relative">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={disabled ? "MedAgent đang xử lý..." : "Describe your symptoms or ask a medical question..."}
            className="w-full h-11 px-4 bg-surface-muted border border-border rounded-xl text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all disabled:opacity-50"
          />
        </div>
        <button
          type="submit"
          disabled={!message.trim() || disabled}
          className="w-11 h-11 bg-primary hover:bg-primary-dark disabled:bg-primary/40 text-white rounded-xl flex items-center justify-center transition-all shrink-0 shadow-sm hover:shadow-md disabled:shadow-none"
        >
          <Send className="w-[18px] h-[18px]" />
        </button>
      </form>
    </div>
  );
}
