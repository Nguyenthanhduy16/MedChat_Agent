import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

import { ToastProvider } from './context/ToastContext';
import { ThemeProvider } from './context/ThemeContext';
import { LanguageProvider } from './context/LanguageContext';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LanguageProvider>
      <ThemeProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </ThemeProvider>
    </LanguageProvider>
  </StrictMode>,
)
