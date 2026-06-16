import { useState, useRef, useEffect } from 'react';
import { LogOut, Pencil, X, Check, User, Mail, AtSign, AlertCircle, ChevronDown } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { cn } from '../../utils/cn';

function getInitials(name = '') {
  return name.split(' ').filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');
}

function ProfilePanel({ onClose }) {
  const { user, logout, updateProfile } = useAuth();
  const [editing, setEditing] = useState(false);
  const [username, setUsername] = useState(user?.username || '');
  const [name, setName]         = useState(user?.name || '');
  const [email, setEmail]       = useState(user?.email || '');
  const [error, setError]       = useState('');
  const [saved, setSaved]       = useState(false);

  const handleSave = () => {
    setError('');
    if (!username.trim()) { setError('Tên đăng nhập không được để trống.'); return; }
    if (!/^[a-zA-Z0-9_]+$/.test(username)) { setError('Tên đăng nhập chỉ dùng chữ, số và dấu _.'); return; }
    if (!name.trim()) { setError('Họ tên không được để trống.'); return; }
    if (email && !/\S+@\S+\.\S+/.test(email)) { setError('Email không hợp lệ.'); return; }
    try {
      updateProfile({ username: username.trim(), name: name.trim(), email });
      setEditing(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCancel = () => {
    setUsername(user?.username || '');
    setName(user?.name || '');
    setEmail(user?.email || '');
    setError('');
    setEditing(false);
  };

  const handleLogout = () => { onClose(); logout(); };

  const inputCls = 'w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors';

  return (
    <div className="w-72 bg-surface border border-border rounded-2xl shadow-panel overflow-hidden animate-fade-in">

      {/* Header */}
      <div className="bg-primary px-5 pt-5 pb-8 relative">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 w-6 h-6 flex items-center justify-center rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
        <div className="flex flex-col items-center gap-2">
          <div className="w-16 h-16 rounded-full bg-white/20 border-2 border-white/40 flex items-center justify-center text-white text-xl font-bold">
            {getInitials(user?.name) || <User className="w-6 h-6" />}
          </div>
          <div className="text-center">
            <p className="text-white font-semibold text-base leading-tight">{user?.name}</p>
            <p className="text-white/70 text-xs mt-0.5">@{user?.username}</p>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="px-5 py-4 -mt-4 relative">
        <div className="bg-surface rounded-xl border border-border p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Thông tin cá nhân
            </span>
            {!editing && (
              <button
                onClick={() => setEditing(true)}
                className="flex items-center gap-1 text-xs text-primary hover:text-primary-dark font-medium transition-colors"
              >
                <Pencil className="w-3 h-3" /> Chỉnh sửa
              </button>
            )}
          </div>

          {error && (
            <div className="flex items-center gap-1.5 text-xs text-danger bg-danger-soft border border-danger/20 rounded-lg px-2.5 py-2 mb-3">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
            </div>
          )}
          {saved && (
            <div className="flex items-center gap-1.5 text-xs text-success bg-success-soft border border-success/20 rounded-lg px-2.5 py-2 mb-3">
              <Check className="w-3.5 h-3.5 shrink-0" /> Đã lưu thành công!
            </div>
          )}

          <div className="flex flex-col gap-3">
            {/* Username */}
            <div>
              <label className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
                <AtSign className="w-3 h-3" /> Tên đăng nhập
              </label>
              {editing
                ? <input value={username} onChange={e => setUsername(e.target.value)} className={inputCls} />
                : <p className="text-sm font-medium text-text-primary">@{user?.username}</p>}
            </div>

            {/* Name */}
            <div>
              <label className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
                <User className="w-3 h-3" /> Họ và tên
              </label>
              {editing
                ? <input value={name} onChange={e => setName(e.target.value)} className={inputCls} />
                : <p className="text-sm font-medium text-text-primary">{user?.name}</p>}
            </div>

            {/* Email */}
            <div>
              <label className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
                <Mail className="w-3 h-3" /> Email
              </label>
              {editing
                ? <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="(tuỳ chọn)" className={inputCls} />
                : <p className="text-sm font-medium text-text-primary">{user?.email || <span className="text-text-muted italic">Chưa cập nhật</span>}</p>}
            </div>
          </div>

          {editing && (
            <div className="flex gap-2 mt-4">
              <button onClick={handleCancel} className="flex-1 py-2 text-xs font-semibold rounded-lg border border-border text-text-secondary hover:bg-surface-hover transition-colors">
                Hủy
              </button>
              <button onClick={handleSave} className="flex-1 py-2 text-xs font-semibold rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors">
                Lưu
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Logout */}
      <div className="px-5 pb-4">
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-border
            text-sm font-semibold text-danger hover:bg-danger-soft hover:border-danger/30 transition-colors"
        >
          <LogOut className="w-4 h-4" /> Đăng xuất
        </button>
      </div>
    </div>
  );
}

export default function UserMenu() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 rounded-full focus:outline-none focus:ring-2 focus:ring-primary/30"
      >
        <div className={cn(
          'w-9 h-9 rounded-full bg-primary flex items-center justify-center text-sm font-semibold text-white',
          'ring-2 ring-transparent hover:ring-primary/30 transition-all',
        )}>
          {getInitials(user?.name) || <User className="w-4 h-4" />}
        </div>
        <ChevronDown className={cn('w-3.5 h-3.5 text-text-muted transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-50">
          <ProfilePanel onClose={() => setOpen(false)} />
        </div>
      )}
    </div>
  );
}
