import { useState } from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  History,
  Settings,
  HelpCircle,
  Plus,
  ArrowLeft,
  Clock,
  Search,
  Trash2,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { useLanguage } from '../../context/LanguageContext';
import { useConversations } from '../../features/chat/hooks/useConversations';

const categories = [
  { id: 1, label: 'Flu & Cold', color: 'bg-orange-500' },
  { id: 2, label: 'Pain Relief', color: 'bg-blue-500' },
  { id: 3, label: 'Skin Care', color: 'bg-emerald-500' },
];

// Mock chat history data
const chatHistoryItems = [
  {
    id: 1,
    title: 'Flu Symptom Assessment',
    preview: 'A fever of 101.4°F combined with body aches...',
    date: 'Hôm nay, 10:45',
    category: 'Flu & Cold',
    categoryColor: 'bg-orange-500',
  },
  {
    id: 2,
    title: 'Tư vấn thuốc giảm đau',
    preview: 'Acetaminophen (Tylenol) là lựa chọn an toàn...',
    date: 'Hôm qua, 14:30',
    category: 'Pain Relief',
    categoryColor: 'bg-blue-500',
  },
  {
    id: 3,
    title: 'Thông tin thuốc Lisinopril',
    preview: 'Lisinopril 10mg được sử dụng để điều trị...',
    date: '28/04/2024',
    category: 'Pain Relief',
    categoryColor: 'bg-blue-500',
  },
  {
    id: 4,
    title: 'Top thuốc bán chạy tháng 4',
    preview: 'Biểu đồ thống kê top 10 thuốc có doanh thu...',
    date: '25/04/2024',
    category: 'Kho hàng',
    categoryColor: 'bg-emerald-500',
  },
  {
    id: 5,
    title: 'Chăm sóc da mùa hè',
    preview: 'Kem chống nắng SPF 50+ kết hợp với...',
    date: '20/04/2024',
    category: 'Skin Care',
    categoryColor: 'bg-emerald-500',
  },
];

export default function Sidebar({ onNewChat, onSelectSession, currentSessionId, onOpenSettings }) {
  const { t } = useLanguage();
  const [showHistory, setShowHistory] = useState(false);
  const { sessions, isLoading: sessionsLoading, deleteSession } = useConversations();

  // ========== CHAT HISTORY VIEW ==========
  if (showHistory) {
    return (
      <aside className="w-[var(--width-sidebar)] bg-surface border-r border-border flex flex-col h-full shrink-0">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border shrink-0">
          <button
            onClick={() => setShowHistory(false)}
            className="w-7 h-7 flex items-center justify-center rounded-md text-text-muted hover:text-primary hover:bg-surface-hover transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <History className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold text-text-primary">
            {t('chatHistory')}
          </h3>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b border-border-light shrink-0">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
            <input
              type="text"
              placeholder={t('searchPlaceholder')}
              className="w-full h-8 pl-8 pr-3 bg-surface-muted border border-border rounded-lg text-xs placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
            />
          </div>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto">
          {sessionsLoading ? (
            <div className="p-4 text-center text-xs text-text-muted">{t('loading')}</div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center text-xs text-text-muted">{t('noHistory')}</div>
          ) : (
            sessions.map((item, index) => (
              <div key={item.id} className="group relative">
                <button
                  onClick={() => {
                    onSelectSession(item.id);
                    setShowHistory(false);
                  }}
                  className={cn(
                    "w-full text-left px-4 py-3 border-b border-border-light hover:bg-surface-hover transition-colors animate-fade-in",
                    currentSessionId === item.id && "bg-primary-soft border-l-2 border-l-primary"
                  )}
                  style={{ animationDelay: `${index * 40}ms` }}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h4 className={cn(
                      "text-[13px] font-medium transition-colors line-clamp-1",
                      currentSessionId === item.id ? "text-primary" : "text-text-primary group-hover:text-primary"
                    )}>
                      {item.title || t('newConversation')}
                    </h4>
                  </div>
                  <p className="text-[11px] text-text-muted line-clamp-1 leading-relaxed mb-1.5">
                    {item.preview || "..."}
                  </p>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3 text-text-muted" />
                    <span className="text-[10px] text-text-muted font-medium">
                      {item.date}
                    </span>
                  </div>
                </button>
                {/* Delete button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Delete this conversation?')) {
                      deleteSession(item.id);
                    }
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 opacity-0 group-hover:opacity-100 text-text-muted hover:text-danger hover:bg-danger-soft rounded-md transition-all z-10"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-border shrink-0">
          <p className="text-[10px] text-text-muted text-center">
            {sessions.length} {t('conversationsCount')}
          </p>
        </div>
      </aside>
    );
  }

  // ========== DEFAULT SIDEBAR VIEW ==========
  return (
    <aside className="w-[var(--width-sidebar)] bg-surface border-r border-border flex flex-col h-full shrink-0">
      {/* Health Dashboard Header */}
      <div className="p-4 pb-3">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-sm">
            <LayoutDashboard className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-text-primary leading-tight">
              Health Dashboard
            </h2>
            <p className="text-xs text-text-muted">Clinical Support</p>
          </div>
        </div>

        <button 
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 h-10 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-lg transition-colors shadow-sm hover:shadow-md"
        >
          <Plus className="w-4 h-4" />
          {t('startConsultation')}
        </button>
      </div>

      {/* Active Threads */}
      <div className="px-4 pt-3 pb-1">
        <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
          {t('activeThreads')}
        </h3>
      </div>
      <nav className="px-2 space-y-0.5">
        {/* Consultations — always active */}
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium bg-primary-soft text-primary border-l-3 border-primary transition-all">
          <MessageSquare className="w-[18px] h-[18px] shrink-0" />
          <span>{t('messages')}</span>
        </button>

        {/* Chat History — opens history view */}
        <button
          onClick={() => setShowHistory(true)}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-all"
        >
          <History className="w-[18px] h-[18px] shrink-0" />
          <span>{t('chatHistory')}</span>
        </button>
      </nav>

      {/* Categories */}
      <div className="px-4 pt-5 pb-1">
        <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
          {t('categories')}
        </h3>
      </div>
      <div className="px-2 space-y-0.5">
        {categories.map((cat) => (
          <button
            key={cat.id}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
          >
            <span className={cn('w-2.5 h-2.5 rounded-full shrink-0', cat.color)}></span>
            <span>{cat.label}</span>
          </button>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Bottom Actions */}
      <div className="p-2 border-t border-border space-y-0.5">
        <button 
          onClick={onOpenSettings}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
        >
          <Settings className="w-[18px] h-[18px]" />
          <span>{t('settings')}</span>
        </button>
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors">
          <HelpCircle className="w-[18px] h-[18px]" />
          <span>{t('support')}</span>
        </button>
      </div>
    </aside>
  );
}
