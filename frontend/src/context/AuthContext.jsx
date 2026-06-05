import { createContext, useContext, useState, useCallback } from 'react';

const USERS_KEY = 'medagent_users';
const SESSION_KEY = 'medagent_session';

const AuthContext = createContext(null);

function loadUsers() {
  try { return JSON.parse(localStorage.getItem(USERS_KEY) || '[]'); }
  catch { return []; }
}
function saveUsers(users) { localStorage.setItem(USERS_KEY, JSON.stringify(users)); }
function loadSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); }
  catch { return null; }
}
function saveSession(session) { localStorage.setItem(SESSION_KEY, JSON.stringify(session)); }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => loadSession());

  const register = useCallback(({ username, name, email, password }) => {
    const users = loadUsers();
    if (users.find(u => u.username === username))
      throw new Error('Tên đăng nhập này đã được sử dụng.');
    if (email && users.find(u => u.email === email && email !== ''))
      throw new Error('Email này đã được đăng ký.');
    const newUser = {
      id: crypto.randomUUID(), username, name, email: email || '',
      password, createdAt: new Date().toISOString(),
    };
    saveUsers([...users, newUser]);
    const session = { id: newUser.id, username, name, email: newUser.email };
    saveSession(session);
    setUser(session);
  }, []);

  const login = useCallback(({ username, password }) => {
    const users = loadUsers();
    const found = users.find(u => u.username === username && u.password === password);
    if (!found) throw new Error('Tên đăng nhập hoặc mật khẩu không đúng.');
    const session = { id: found.id, username: found.username, name: found.name, email: found.email };
    saveSession(session);
    setUser(session);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(SESSION_KEY);
    setUser(null);
  }, []);

  const updateProfile = useCallback(({ username, name, email }) => {
    const users = loadUsers();
    const idx = users.findIndex(u => u.id === user?.id);
    if (idx === -1) throw new Error('Không tìm thấy tài khoản.');
    if (username !== users[idx].username && users.find(u => u.username === username))
      throw new Error('Tên đăng nhập này đã được sử dụng.');
    if (email && email !== users[idx].email && users.find(u => u.email === email && email !== ''))
      throw new Error('Email này đã được dùng bởi tài khoản khác.');
    users[idx] = { ...users[idx], username, name, email: email || '' };
    saveUsers(users);
    const session = { id: users[idx].id, username, name, email: users[idx].email };
    saveSession(session);
    setUser(session);
  }, [user]);

  const changePassword = useCallback(({ currentPassword, newPassword }) => {
    const users = loadUsers();
    const idx = users.findIndex(u => u.id === user?.id);
    if (idx === -1) throw new Error('Không tìm thấy tài khoản.');
    if (users[idx].password !== currentPassword) throw new Error('Mật khẩu hiện tại không đúng.');
    users[idx] = { ...users[idx], password: newPassword };
    saveUsers(users);
  }, [user]);

  return (
    <AuthContext.Provider value={{ user, register, login, logout, updateProfile, changePassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
