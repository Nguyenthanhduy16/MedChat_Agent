import { useState } from 'react';
import {
  Shield, Eye, EyeOff, Mail, Lock, User,
  ArrowRight, CheckCircle2, Activity, Pill,
  BarChart3, AlertCircle, X,
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
    <div className="min-h-screen flex bg-surface animate-fade-in relative">

      {onClose && (
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-50 w-8 h-8 flex items-center justify-center rounded-full
            bg-surface-hover border border-border text-text-muted hover:text-text-primary hover:bg-surface transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      )}

      {/* ===== LEFT PANEL — Branding ===== */}
      <div className="hidden lg:flex lg:w-[45%] bg-primary flex-col justify-between p-10 relative overflow-hidden">
        {/* Background blobs */}
        <div className="absolute -top-20 -left-20 w-80 h-80 bg-white/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-20 -right-10 w-96 h-96 bg-white/5 rounded-full blur-3xl" />

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center backdrop-blur-sm overflow-hidden bg-white">
            <img src="/logo.png" alt="MedAgent" className="w-full h-full object-cover" />
          </div>
          <span className="text-white text-xl font-bold tracking-tight">MedAgent</span>
        </div>

        {/* Center content */}
        <div className="relative">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm text-white/90 text-xs font-semibold
            px-3 py-1.5 rounded-full mb-6 uppercase tracking-wider">
            <Shield className="w-3.5 h-3.5" /> Nền tảng tư vấn dược AI
          </div>
          <h1 className="text-3xl font-bold text-white leading-tight mb-4">
            Trợ lý dược phẩm<br />thông minh của bạn
          </h1>
          <p className="text-white/70 text-sm leading-relaxed mb-8">
            Tra cứu thông tin thuốc, phân tích kho hàng và nhận tư vấn
            chuyên sâu được hỗ trợ bởi AI — mọi lúc, mọi nơi.
          </p>
          <ul className="flex flex-col gap-3">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-white/80 text-sm">
                <div className="w-7 h-7 bg-white/15 rounded-lg flex items-center justify-center shrink-0">
                  <Icon className="w-3.5 h-3.5 text-white" />
                </div>
                {text}
              </li>
            ))}
          </ul>
        </div>

        {/* Footer */}
        <div className="relative flex items-center gap-2 text-white/40 text-xs">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Dữ liệu cục bộ — không chia sẻ bên ngoài
        </div>
      </div>

      {/* ===== RIGHT PANEL — Form ===== */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">

          {/* Mobile logo */}
          <div className="flex lg:hidden items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden bg-white">
              <img src="/logo.png" alt="MedAgent" className="w-full h-full object-cover" />
            </div>
            <span className="text-lg font-bold text-primary">MedAgent</span>
          </div>

          {/* Heading */}
          <div className="mb-7">
            <h2 className="text-2xl font-bold text-text-primary mb-1">
              {tab === 'login' ? 'Chào mừng trở lại' : 'Tạo tài khoản mới'}
            </h2>
            <p className="text-sm text-text-secondary">
              {tab === 'login'
                ? 'Đăng nhập để tiếp tục sử dụng MedAgent.'
                : 'Đăng ký để bắt đầu trải nghiệm MedAgent.'}
            </p>
          </div>

          {/* Tab switcher */}
          <div className="flex bg-surface-muted rounded-lg p-1 mb-6 border border-border">
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
                    ? 'bg-surface text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary',
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Form */}
          {tab === 'login'
            ? <LoginForm    onSuccess={onAuthenticated} />
            : <RegisterForm onSuccess={onAuthenticated} />
          }

          {/* Switch tab link */}
          <p className="text-center text-sm text-text-secondary mt-6">
            {tab === 'login' ? 'Chưa có tài khoản? ' : 'Đã có tài khoản? '}
            <button
              onClick={() => setTab(tab === 'login' ? 'register' : 'login')}
              className="text-primary font-semibold hover:underline"
            >
              {tab === 'login' ? 'Đăng ký ngay' : 'Đăng nhập'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
