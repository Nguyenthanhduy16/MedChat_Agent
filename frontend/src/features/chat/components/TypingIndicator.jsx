import { Bot } from 'lucide-react';

export default function TypingIndicator() {
  return (
    <div className="flex gap-3 justify-start animate-fade-in mb-4">
      {/* Bot Avatar */}
      <div className="w-8 h-8 bg-surface-muted border border-border rounded-full flex items-center justify-center shrink-0 mt-1 shadow-sm overflow-hidden">
        <img src="/logo.png" alt="MedAgent" className="w-full h-full object-cover" />
      </div>

      <div className="max-w-[80%] space-y-1">
        <div className="bg-surface border border-border text-text-primary rounded-2xl px-4 py-3 shadow-sm">
          <div className="flex items-center gap-1 h-5">
            <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            <span className="text-[11px] text-text-muted font-medium ml-2 uppercase tracking-wider">
              MedAgent đang xử lý...
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
