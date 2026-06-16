import { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import AuthPage from './pages/AuthPage';
import LandingPage from './pages/LandingPage';
import ChatPage from './pages/ChatPage';

function AppRoutes() {
  const [currentPage, setCurrentPage] = useState('landing');
  const [returnPage, setReturnPage] = useState('landing');

  const goToAuth = (from = 'landing') => {
    setReturnPage(from);
    setCurrentPage('auth');
  };

  if (currentPage === 'auth') {
    return (
      <AuthPage
        onAuthenticated={() => setCurrentPage(returnPage)}
        onClose={() => setCurrentPage(returnPage)}
      />
    );
  }

  if (currentPage === 'chat') {
    return (
      <ChatPage
        onBack={() => setCurrentPage('landing')}
        onShowAuth={() => goToAuth('chat')}
      />
    );
  }

  return (
    <LandingPage
      onStartChat={() => setCurrentPage('chat')}
      onShowAuth={() => goToAuth('landing')}
    />
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
