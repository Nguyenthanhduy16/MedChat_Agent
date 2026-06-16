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

export default function ChatPage({ onBack, onShowAuth }) {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);

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
    <div className="h-screen flex flex-col overflow-hidden">
      {/* ===== TOP BAR ===== */}
      <header className="h-14 bg-surface border-b border-border flex items-center px-4 shrink-0 sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">M</span>
          </div>
          <span className="text-lg font-bold text-primary tracking-tight">MedAgent</span>
        </div>

        <nav className="flex items-center gap-1 ml-8">
          <button
            onClick={onBack}
            className="px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-hover rounded-md transition-colors"
          >
            {t('dashboard')}
          </button>
          <button className="px-3 py-1.5 text-sm font-medium text-primary border-b-2 border-primary rounded-md transition-colors">
            {t('messages')}
          </button>
        </nav>

        <div className="flex-1" />

        <div className="flex items-center gap-3">
          <LanguageSwitcher />

          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs font-medium text-text-muted hover:text-primary transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            {t('backToHome')}
          </button>

          {user ? (
            <UserMenu />
          ) : (
            <>
              <button
                onClick={() => onShowAuth?.()}
                className="px-4 py-1.5 text-sm font-semibold text-text-primary border border-border rounded-lg hover:bg-surface-hover transition-colors"
              >
                Đăng nhập
              </button>
              <button
                onClick={() => onShowAuth?.()}
                className="px-4 py-1.5 text-sm font-semibold text-white bg-primary rounded-lg hover:bg-primary-dark transition-colors"
              >
                Đăng ký
              </button>
            </>
          )}
        </div>
      </header>

      {/* ===== MAIN CONTENT ===== */}
      <div className={cn(
        'flex flex-1 overflow-hidden transition-all duration-300',
        isSettingsOpen && 'blur-sm scale-[0.99] pointer-events-none',
      )}>
        <Sidebar
          onNewChat={newConversation}
          onSelectSession={loadHistory}
          currentSessionId={currentSessionId}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />
        <main className="flex-1 overflow-hidden">
          <ChatThread
            messages={messages}
            isLoading={isLoading}
            error={error}
            sendMessage={sendMessage}
            onRetry={retry}
            onRequireAuth={user ? undefined : handleRequireAuth}
          />
        </main>
        <RightPanel />
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
