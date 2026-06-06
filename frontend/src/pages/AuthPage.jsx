import { useState } from 'react';
import {
  Shield, Eye, EyeOff, Mail, Lock, User,
  ArrowRight, CheckCircle2, Activity, Pill,
  BarChart3, AlertCircle, X, Phone
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { cn } from '../utils/cn';

const FEATURES = [
  { icon: Pill,       text: 'Tư vấn dược phẩm thông minh' },
  { icon: Activity,   text: 'Phân tích dữ liệu kho thuốc' },
  { icon: BarChart3,  text: 'Biểu đồ thống kê trực quan' },
  { icon: Shield,     text: 'Dữ liệu được bảo mật an toàn' },
];

function Field({ label, id, type = 'text', value, onChange, placeholder, icon: Icon, error }) {
  const [show, setShow] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword ? (show ? 'text' : 'password') : type;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-text-primary">
        {label}
      </label>
      <div className="relative">
        <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
        <input
          id={id}
          type={inputType}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className={cn(
            'w-full pl-10 pr-10 py-2.5 rounded-lg border bg-surface text-sm text-text-primary',
            'placeholder:text-text-muted transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
            error ? 'border-danger' : 'border-border hover:border-primary/40',
          )}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow(s => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
          >
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
      {error && (
        <p className="text-xs text-danger flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5" /> {error}
        </p>
      )}
    </div>
  );
}

function LoginForm({ onSuccess }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const validate = () => {
    const e = {};
    if (!username.trim()) e.username = 'Vui lòng nhập tên đăng nhập.';
    if (!password) e.password = 'Vui lòng nhập mật khẩu.';
    return e;
  };

  const handleSubmit = async e => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    try {
      await new Promise(r => setTimeout(r, 400));
      login({ username: username.trim(), password });
      onSuccess();
    } catch (err) {
      setErrors({ form: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {errors.form && (
        <div className="flex items-center gap-2 text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-3 py-2.5">
          <AlertCircle className="w-4 h-4 shrink-0" /> {errors.form}
        </div>
      )}
      <Field label="Tên đăng nhập" id="login-username" value={username} onChange={setUsername}
        placeholder="Nhập tên đăng nhập" icon={User} error={errors.username} />
      <Field label="Mật khẩu" id="login-password" type="password" value={password} onChange={setPassword}
        placeholder="Nhập mật khẩu" icon={Lock} error={errors.password} />
      <button
        type="submit"
        disabled={loading}
        className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-primary text-white text-sm font-semibold
          hover:bg-primary-dark transition-colors shadow-sm disabled:opacity-60 disabled:cursor-not-allowed mt-1"
      >
        {loading ? (
          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <> Đăng nhập <ArrowRight className="w-4 h-4" /> </>
        )}
      </button>
    </form>
  );
}

function RegisterForm({ onSuccess }) {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const validate = () => {
    const e = {};
    if (!username.trim()) e.username = 'Vui lòng nhập tên đăng nhập.';
    else if (!/^[a-zA-Z0-9_]+$/.test(username)) e.username = 'Chỉ dùng chữ, số và dấu _';
    if (!name.trim()) e.name = 'Vui lòng nhập họ tên.';
    if (email && !/\S+@\S+\.\S+/.test(email)) e.email = 'Email không hợp lệ.';
    if (!password) e.password = 'Vui lòng nhập mật khẩu.';
    else if (password.length < 6) e.password = 'Mật khẩu tối thiểu 6 ký tự.';
    if (!confirm) e.confirm = 'Vui lòng xác nhận mật khẩu.';
    else if (confirm !== password) e.confirm = 'Mật khẩu không khớp.';
    return e;
  };

  const handleSubmit = async e => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    try {
      await new Promise(r => setTimeout(r, 400));
      register({ username: username.trim(), name: name.trim(), email, password });
      onSuccess();
    } catch (err) {
      setErrors({ form: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {errors.form && (
        <div className="flex items-center gap-2 text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-3 py-2.5">
          <AlertCircle className="w-4 h-4 shrink-0" /> {errors.form}
        </div>
      )}
      <Field label="Tên đăng nhập" id="reg-username" value={username} onChange={setUsername}
        placeholder="vd: nguyen_van_a" icon={User} error={errors.username} />
      <Field label="Họ và tên" id="reg-name" value={name} onChange={setName}
        placeholder="Nguyễn Văn A" icon={User} error={errors.name} />
      <Field label="Email (tuỳ chọn)" id="reg-email" type="email" value={email} onChange={setEmail}
        placeholder="you@example.com" icon={Mail} error={errors.email} />
      <Field label="Mật khẩu" id="reg-password" type="password" value={password} onChange={setPassword}
        placeholder="Tối thiểu 6 ký tự" icon={Lock} error={errors.password} />
      <Field label="Xác nhận mật khẩu" id="reg-confirm" type="password" value={confirm} onChange={setConfirm}
        placeholder="Nhập lại mật khẩu" icon={Lock} error={errors.confirm} />
      <button
        type="submit"
        disabled={loading}
        className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-primary text-white text-sm font-semibold
          hover:bg-primary-dark transition-colors shadow-sm disabled:opacity-60 disabled:cursor-not-allowed mt-1"
      >
        {loading ? (
          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <> Tạo tài khoản <ArrowRight className="w-4 h-4" /> </>
        )}
      </button>
    </form>
  );
}

export default function AuthPage({ onAuthenticated, onClose }) {
  const [tab, setTab] = useState('login');

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-fade-in">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      
      {/* Modal Container */}
      <div className="relative w-full max-w-[420px] bg-white rounded-2xl shadow-xl flex flex-col overflow-hidden">
        
        {onClose && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-full text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}

        <div className="px-8 pt-10 pb-8 flex flex-col items-center">
          {/* Heading */}
          <div className="mb-6 text-center w-full">
            <h2 className="text-[22px] font-semibold text-text-primary mb-3">
              {tab === 'login' ? 'Đăng nhập hoặc đăng ký' : 'Tạo tài khoản mới'}
            </h2>
            <p className="text-sm text-text-secondary leading-relaxed max-w-[300px] mx-auto">
              {tab === 'login'
                ? 'Bạn sẽ nhận được phản hồi thông minh hơn và có thể tải lên tệp, hình ảnh, v.v.'
                : 'Đăng ký để bắt đầu trải nghiệm hệ thống trò chuyện thông minh.'}
            </p>
          </div>

          {/* Social Auth Buttons */}
          {tab === 'login' && (
            <>
              <div className="flex flex-col gap-3 w-full mb-6">
                <button className="flex items-center justify-center gap-2.5 w-full py-2.5 border border-border rounded-full hover:bg-surface-hover transition-colors text-[15px] font-semibold text-text-primary">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 48 48">
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                  </svg>
                  Tiếp tục với Google
                </button>
                <button className="flex items-center justify-center gap-2.5 w-full py-2.5 border border-border rounded-full hover:bg-surface-hover transition-colors text-[15px] font-semibold text-text-primary">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M11.182.008C11.148-.03 9.923.023 8.857 1.18c-1.066 1.156-.902 2.482-.878 2.516.024.034 1.52.087 2.475-1.258.955-1.345.762-2.391.728-2.43Zm3.314 11.733c-.048-.096-2.325-1.234-2.113-3.422.212-2.189 1.675-2.789 1.698-2.854.023-.065-.597-.79-1.254-1.157a3.692 3.692 0 0 0-1.563-.434c-1.082-.031-2.203.456-2.836.456-.634 0-1.736-.456-2.835-.456C4.721 3.87 3.1 4.544 2.122 5.923.642 8.01.664 11.168 2.155 13.56c.742 1.196 1.658 2.404 2.94 2.404 1.282 0 1.554-.775 3.125-.775 1.571 0 1.843.775 3.125.775 1.282 0 2.198-1.208 2.94-2.404.742-1.196 1.484-3.033 1.484-3.033Z"/>
                  </svg>
                  Tiếp tục với Apple
                </button>
                <button className="flex items-center justify-center gap-2.5 w-full py-2.5 border border-border rounded-full hover:bg-surface-hover transition-colors text-[15px] font-semibold text-text-primary">
                  <Phone className="w-[18px] h-[18px]" />
                  Tiếp tục với số điện thoại
                </button>
              </div>

              {/* Divider */}
              <div className="flex items-center w-full gap-4 mb-6">
                <div className="flex-1 h-px bg-border"></div>
                <span className="text-xs font-semibold text-text-muted">HOẶC</span>
                <div className="flex-1 h-px bg-border"></div>
              </div>
            </>
          )}

          {/* Tab switcher */}
          <div className="flex w-full bg-surface-muted rounded-lg p-1 mb-6 border border-border">
            {[
              { key: 'login',    label: 'Đăng nhập' },
              { key: 'register', label: 'Đăng ký'   },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={cn(
                  'flex-1 py-2 text-sm font-semibold rounded-md transition-all',
                  tab === key
                    ? 'bg-white text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary',
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Form */}
          <div className="w-full">
            {tab === 'login'
              ? <LoginForm    onSuccess={onAuthenticated} />
              : <RegisterForm onSuccess={onAuthenticated} />
            }
          </div>
        </div>
      </div>
    </div>
  );
}
