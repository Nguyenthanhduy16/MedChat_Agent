import { useState } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import LanguageSwitcher from '../features/chat/components/LanguageSwitcher';
import UserMenu from '../components/ui/UserMenu';
import Sidebar from '../components/layout/Sidebar';
import RightPanel from '../components/layout/RightPanel';
import ChatThread from '../features/chat/components/ChatThread';
import SettingsModal from '../features/chat/components/SettingsModal';
import { ArrowLeft, LogIn, X } from 'lucide-react';
import { cn } from '../utils/cn';
import { useChat } from '../features/chat/hooks/useChat';

function LoginPromptModal({ onClose, onShowAuth }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-2xl shadow-panel p-6 w-80 animate-fade-in">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 w-7 h-7 flex items-center justify-center rounded-full text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="w-12 h-12 bg-primary-soft rounded-xl flex items-center justify-center mb-4">
          <LogIn className="w-6 h-6 text-primary" />
        </div>

        <h3 className="text-base font-bold text-text-primary mb-1">
          Đăng nhập để tiếp tục
        </h3>
        <p className="text-sm text-text-secondary mb-5 leading-relaxed">
          Bạn cần đăng nhập để gửi tin nhắn và lưu lịch sử trò chuyện.
        </p>

        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 text-sm font-semibold rounded-lg border border-border text-text-secondary hover:bg-surface-hover transition-colors"
          >
            Để sau
          </button>
          <button
            onClick={onShowAuth}
            className="flex-1 py-2.5 text-sm font-semibold rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors"
          >
            Đăng nhập
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage({ onShowAuth }) {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const {
    messages,
    isLoading,
    error,
    currentSessionId,
    sendMessage,
    newConversation,
    loadHistory,
    retry
  } = useChat();

  const handleRequireAuth = () => setShowLoginPrompt(true);

  const handleGoAuth = () => {
    setShowLoginPrompt(false);
    onShowAuth?.();
  };

  return (
    <div className="absolute inset-0 flex flex-col overflow-hidden bg-white">
      {/* ===== TOP BAR (Mobile Only) ===== */}
      <header className="h-14 bg-white border-b border-border flex items-center px-4 shrink-0 sticky top-0 z-50 justify-between md:hidden">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="w-9 h-9 flex items-center justify-center rounded-md text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
            title="Toggle Sidebar"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>
          </button>
          <span className="text-lg font-bold text-text-primary tracking-tight">MedChat</span>
        </div>
      </header>

      {/* ===== MAIN CONTENT ===== */}
      <div className={cn(
        'flex flex-1 min-h-0 overflow-hidden transition-all duration-300 bg-white relative',
        isSettingsOpen && 'blur-sm scale-[0.99] pointer-events-none',
      )}>
        {/* Desktop Sidebar Container */}
        <div 
          className={cn(
            "h-full flex flex-col transition-all duration-300 ease-in-out shrink-0 overflow-hidden hidden md:block",
            isSidebarOpen ? "w-[var(--width-sidebar)]" : "w-[68px]"
          )}
        >
          <Sidebar
            onNewChat={newConversation}
            onSelectSession={loadHistory}
            currentSessionId={currentSessionId}
            onOpenSettings={() => setIsSettingsOpen(true)}
            isOpen={isSidebarOpen}
            onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
            onShowAuth={onShowAuth}
          />
        </div>

        {/* Mobile Sidebar Overlay */}
        <div className={cn(
          "fixed inset-0 bg-black/40 backdrop-blur-sm z-40 md:hidden transition-opacity",
          isSidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )} onClick={() => setIsSidebarOpen(false)} />
        
        <div className={cn(
          "fixed inset-y-0 left-0 z-50 h-full flex flex-col w-[var(--width-sidebar)] transform transition-transform duration-300 ease-in-out md:hidden shadow-2xl",
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}>
          <Sidebar
            onNewChat={newConversation}
            onSelectSession={loadHistory}
            currentSessionId={currentSessionId}
            onOpenSettings={() => setIsSettingsOpen(true)}
            onShowAuth={onShowAuth}
          />
        </div>

        <main className="flex-1 overflow-hidden bg-white min-w-0 relative">
          <ChatThread
            messages={messages}
            isLoading={isLoading}
            error={error}
            sendMessage={sendMessage}
            onRetry={retry}
            onRequireAuth={undefined} // user ? undefined : handleRequireAuth
          />
        </main>
      </div>

      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {showLoginPrompt && (
        <LoginPromptModal
          onClose={() => setShowLoginPrompt(false)}
          onShowAuth={handleGoAuth}
        />
      )}
    </div>
  );
}
