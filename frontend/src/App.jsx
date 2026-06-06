import { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import AuthPage from './pages/AuthPage';
import ChatPage from './pages/ChatPage';

function AppRoutes() {
  const [showAuth, setShowAuth] = useState(false);

  return (
    <>
      <ChatPage
        onShowAuth={() => setShowAuth(true)}
      />
      {showAuth && (
        <AuthPage
          onAuthenticated={() => setShowAuth(false)}
          onClose={() => setShowAuth(false)}
        />
      )}
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
