import { useState } from 'react';
import { Shield, Lock, Eye, EyeOff, AlertCircle, Check } from 'lucide-react';
import { useAuth } from '../../../../context/AuthContext';
import { cn } from '../../../../utils/cn';
import Toggle from './Toggle';

function PasswordField({ id, label, value, onChange, placeholder, error }) {
  const [show, setShow] = useState(false);
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-xs font-bold text-text-muted uppercase tracking-wider block">
        {label}
      </label>
      <div className="relative">
        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
        <input
          id={id}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className={cn(
            'w-full h-11 pl-10 pr-10 bg-surface-muted border rounded-xl text-sm',
            'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors',
            error ? 'border-danger' : 'border-border',
          )}
        />
        <button
          type="button"
          onClick={() => setShow(s => !s)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      {error && (
        <p className="text-xs text-danger flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5" /> {error}
        </p>
      )}
    </div>
  );
}

export default function SecurityTab({ twoFactor, onToggle2FA }) {
  const { user, changePassword } = useAuth();

  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState({});
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const validate = () => {
    const e = {};
    if (!current) e.current = 'Vui lòng nhập mật khẩu hiện tại.';
    if (!next) e.next = 'Vui lòng nhập mật khẩu mới.';
    else if (next.length < 6) e.next = 'Mật khẩu tối thiểu 6 ký tự.';
    else if (next === current) e.next = 'Mật khẩu mới phải khác mật khẩu hiện tại.';
    if (!confirm) e.confirm = 'Vui lòng xác nhận mật khẩu mới.';
    else if (confirm !== next) e.confirm = 'Mật khẩu xác nhận không khớp.';
    return e;
  };

  const handleSubmit = async e => {
    e.preventDefault();
    if (!user) return;
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    try {
      await new Promise(r => setTimeout(r, 300));
      changePassword({ currentPassword: current, newPassword: next });
      setCurrent(''); setNext(''); setConfirm('');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setErrors({ current: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* ===== Password Change ===== */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-widest border-b border-border pb-3">
          Đổi mật khẩu
        </h3>

        {!user && (
          <div className="flex items-center gap-2 text-sm text-text-muted bg-surface-muted border border-border rounded-xl px-4 py-3">
            <Shield className="w-4 h-4 shrink-0" />
            Bạn cần đăng nhập để thay đổi mật khẩu.
          </div>
        )}

        {errors.form && (
          <div className="flex items-center gap-2 text-sm text-danger bg-danger-soft border border-danger/20 rounded-xl px-4 py-3">
            <AlertCircle className="w-4 h-4 shrink-0" /> {errors.form}
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 text-sm text-success bg-success-soft border border-success/20 rounded-xl px-4 py-3">
            <Check className="w-4 h-4 shrink-0" /> Đổi mật khẩu thành công!
          </div>
        )}

        <PasswordField
          id="pw-current" label="Mật khẩu hiện tại"
          value={current} onChange={setCurrent}
          placeholder="Nhập mật khẩu hiện tại" error={errors.current}
        />
        <div className="grid grid-cols-2 gap-4">
          <PasswordField
            id="pw-new" label="Mật khẩu mới"
            value={next} onChange={setNext}
            placeholder="Tối thiểu 6 ký tự" error={errors.next}
          />
          <PasswordField
            id="pw-confirm" label="Xác nhận mật khẩu mới"
            value={confirm} onChange={setConfirm}
            placeholder="Nhập lại mật khẩu mới" error={errors.confirm}
          />
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!user || loading}
            className="h-10 px-6 bg-primary text-white text-sm font-semibold rounded-xl
              hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed
              flex items-center gap-2"
          >
            {loading && <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            Lưu mật khẩu mới
          </button>
        </div>
      </form>

      {/* ===== 2FA ===== */}
      <div className="p-5 bg-primary-soft/30 rounded-2xl border border-primary/20 flex items-center justify-between">
        <div className="flex gap-4">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-text-primary">Xác thực hai bước (2FA)</h4>
            <p className="text-xs text-text-muted mt-1">Bảo vệ tài khoản với lớp bảo mật bổ sung.</p>
          </div>
        </div>
        <Toggle active={twoFactor} onToggle={onToggle2FA} />
      </div>
    </div>
  );
}
