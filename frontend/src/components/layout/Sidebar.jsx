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
  Hexagon,
  User,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { useLanguage } from '../../context/LanguageContext';
import { useConversations } from '../../features/chat/hooks/useConversations';
import { useAuth } from '../../context/AuthContext';

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

export default function Sidebar({ onNewChat, onSelectSession, currentSessionId, onOpenSettings, isOpen = true, onToggle, onShowAuth }) {
  const { t } = useLanguage();
  const { sessions, isLoading: sessionsLoading, deleteSession } = useConversations();
  const { user } = useAuth();

  if (!isOpen) {
    return (
      <aside className="w-[68px] bg-surface-muted border-r border-border flex flex-col h-full shrink-0 items-center py-3">
        <button 
          onClick={onToggle} 
          className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface transition-colors mb-4 text-text-secondary hover:text-text-primary" 
          title="Mở thanh bên"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>
        </button>

        <button 
          onClick={onNewChat} 
          className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface transition-colors mb-2 text-text-secondary hover:text-text-primary" 
          title="Đoạn chat mới"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
        </button>

        <button className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface transition-colors mb-2 text-text-secondary hover:text-text-primary" title="Tìm kiếm">
          <Search className="w-5 h-5" />
        </button>

        <div className="flex-1"></div>

        <button onClick={onOpenSettings} className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface transition-colors mb-2 text-text-secondary hover:text-text-primary" title="Cài đặt">
          <Settings className="w-5 h-5" />
        </button>

        <button 
          onClick={user ? undefined : onShowAuth}
          className="w-10 h-10 flex items-center justify-center rounded-full bg-surface border border-border shadow-sm hover:bg-surface-hover transition-colors text-text-secondary overflow-hidden shrink-0 mt-2"
          title={user ? "Hồ sơ của bạn" : "Đăng nhập"}
        >
          {user ? (
            <div className="w-full h-full bg-primary flex items-center justify-center text-[13px] font-semibold text-white">
              {user.name ? user.name.split(' ').filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('') : <User className="w-5 h-5" />}
            </div>
          ) : (
            <User className="w-5 h-5" />
          )}
        </button>
      </aside>
    );
  }

  return (
    <aside className="w-[var(--width-sidebar)] h-full bg-surface-muted border-r border-border flex flex-col overflow-hidden flex-1 min-h-0">
      {/* Header: Logo and Toggle */}
      <div className="px-3 pt-3 pb-1 flex items-center justify-between">
        <div className="flex items-center gap-2 pl-2 mt-1">
          <img src="/logo.png" alt="MedAgent" className="w-7 h-7 object-cover rounded-md" />
          <span className="text-[17px] font-bold text-text-primary tracking-tight">MedChat</span>
        </div>
        <button 
          onClick={onToggle}
          className="w-10 h-10 flex items-center justify-center rounded-lg text-text-secondary hover:bg-surface hover:text-text-primary transition-colors shrink-0"
          title="Đóng thanh bên"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>
        </button>
      </div>

      {/* New Chat & Search Buttons */}
      <div className="px-3 pb-2 space-y-0.5">
        <button 
          onClick={onNewChat}
          className="w-full flex items-center justify-start gap-2.5 h-10 px-3 bg-surface border border-border/50 hover:bg-surface-hover text-text-primary text-[14px] font-medium rounded-xl transition-colors shadow-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
          <span className="truncate">Đoạn chat mới</span>
        </button>
        
        <button className="w-full flex items-center justify-start gap-2.5 h-10 px-3 hover:bg-surface text-text-primary text-[14px] rounded-lg transition-colors group mt-1">
          <Search className="w-[18px] h-[18px] text-text-secondary group-hover:text-text-primary transition-colors" />
          <span className="truncate">Tìm kiếm đoạn chat</span>
        </button>
      </div>

      {/* History List - flex-1 chiếm khoảng trống giữa, scroll nội bộ */}
      <div className="flex-1 min-h-[clamp(180px,28vh,260px)] overflow-y-auto px-2 pb-2 space-y-0.5">
        <div className="px-2 py-2">
          <span className="text-xs font-semibold text-text-muted">Hôm nay</span>
        </div>
        
        {sessionsLoading ? (
          <div className="p-2 text-xs text-text-muted">{t('loading')}</div>
        ) : sessions.length === 0 ? (
          <div className="p-2 text-xs text-text-muted">{t('noHistory')}</div>
        ) : (
          sessions.map((item) => (
            <div key={item.id} className="group relative">
              <button
                onClick={() => onSelectSession(item.id)}
                className={cn(
                  "w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm transition-colors text-left",
                  currentSessionId === item.id 
                    ? "bg-surface text-text-primary font-medium" 
                    : "text-text-secondary hover:bg-surface hover:text-text-primary"
                )}
              >
                <MessageSquare className="w-4 h-4 shrink-0 opacity-70" />
                <span className="truncate flex-1">{item.title || t('newConversation')}</span>
              </button>
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm('Delete this conversation?')) deleteSession(item.id);
                }}
                className="absolute right-1 top-1/2 -translate-y-1/2 p-1.5 opacity-0 group-hover:opacity-100 text-text-muted hover:text-danger rounded-md transition-all z-10 bg-gradient-to-l from-surface to-transparent"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      <div className="mt-auto shrink-0">
      {/* Bottom Actions */}
      <div className="p-2 space-y-0.5">
        <button className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-text-primary hover:bg-surface transition-colors">
          <Hexagon className="w-[18px] h-[18px] text-text-secondary" />
          <span className="truncate">Xem các gói dịch vụ và mức giá</span>
        </button>
        <button 
          onClick={onOpenSettings}
          className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-text-primary hover:bg-surface transition-colors"
        >
          <Settings className="w-[18px] h-[18px] text-text-secondary" />
          <span className="truncate">Cài đặt</span>
        </button>
        <button className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-text-primary hover:bg-surface transition-colors">
          <HelpCircle className="w-[18px] h-[18px] text-text-secondary" />
          <span className="truncate">Trợ giúp</span>
        </button>
      </div>

      {!user && (
        <div className="px-4 pb-4 pt-3 mt-1 border-t border-border">
          <h4 className="text-[15px] font-semibold text-text-primary mb-2 leading-snug pr-4">
            Nhận phản hồi phù hợp với nhu cầu của bạn
          </h4>
          <p className="text-[13px] text-text-secondary mb-4 leading-relaxed">
            Đăng nhập để nhận câu trả lời dựa trên các đoạn chat đã lưu, cũng như tạo hình ảnh và tải lên tệp.
          </p>
          <button 
            onClick={onShowAuth}
            className="w-full py-2 bg-white border border-border shadow-sm text-text-primary text-[14px] font-bold rounded-full hover:bg-surface-hover transition-colors"
          >
            Đăng nhập
          </button>
        </div>
      )}
      </div>
    </aside>
  );
}
