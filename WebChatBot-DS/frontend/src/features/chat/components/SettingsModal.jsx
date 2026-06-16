import { useState } from 'react';
import { useLanguage } from '../../../context/LanguageContext';
import { 
  User, 
  Shield, 
  Moon, 
  X
} from 'lucide-react';
import { cn } from '../../../utils/cn';

// Sub-components
import ProfileTab from './settings/ProfileTab';
import SecurityTab from './settings/SecurityTab';
import AppearanceTab from './settings/AppearanceTab';

export default function SettingsModal({ isOpen, onClose }) {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState('appearance');
  
  // Appearance State
  const [fontSize, setFontSize] = useState(50);
  const [accentColor, setAccentColor] = useState('blue');

  // Security State
  const [security, setSecurity] = useState({
    twoFactor: true
  });

  if (!isOpen) return null;

  const tabs = [
    { id: 'profile', label: t('profile'), icon: User },
    { id: 'security', label: t('security'), icon: Shield },
    { id: 'appearance', label: t('appearance'), icon: Moon },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 light">
      {/* Backdrop with Blur */}
      <div 
        className="absolute inset-0 bg-black/40 backdrop-blur-md animate-fade-in"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div className="relative w-full max-w-4xl h-[680px] bg-white rounded-3xl shadow-2xl flex overflow-hidden animate-scale-in">
        
        {/* Left Sidebar */}
        <aside className="w-64 bg-[#F8FAFC] border-r border-border flex flex-col p-6">
          <div className="mb-8 px-2">
            <h2 className="text-xl font-bold text-primary">{t('settings')}</h2>
            <p className="text-xs text-text-muted mt-1 leading-relaxed">Manage your healthcare preferences</p>
          </div>

          <nav className="flex-1 space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all group",
                    isActive 
                      ? "bg-white text-primary shadow-sm border border-border/50" 
                      : "text-text-secondary hover:bg-white/50 hover:text-text-primary"
                  )}
                >
                  <Icon className={cn("w-[18px] h-[18px] transition-colors", isActive ? "text-primary" : "text-text-muted group-hover:text-text-primary")} />
                  {tab.label}
                  {isActive && <div className="ml-auto w-1 h-4 bg-primary rounded-full animate-fade-in" />}
                </button>
              );
            })}
          </nav>

          {/* Mini Profile Card */}
          <div className="mt-auto pt-6 border-t border-border/60">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-primary-soft flex items-center justify-center overflow-hidden border border-primary/20 shadow-sm">
                <img 
                  src="https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?q=80&w=100&auto=format&fit=crop" 
                  alt="Doctor"
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="overflow-hidden">
                <p className="text-sm font-bold text-text-primary truncate">Alex Chen, M.D.</p>
                <p className="text-[10px] text-text-muted truncate font-medium">a.chen@hospital.org</p>
              </div>
            </div>
            <button className="w-full py-2.5 bg-[#003594] hover:bg-[#002870] text-white text-[11px] font-bold rounded-lg uppercase tracking-wider transition-colors shadow-sm">
              Edit Profile
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col bg-white">
          <header className="px-8 py-6 flex items-center justify-between shrink-0">
            <div>
              <h1 className="text-3xl font-extrabold text-text-primary tracking-tight capitalize">
                {activeTab}
              </h1>
              <p className="text-sm text-text-secondary mt-1">
                {activeTab === 'profile' && 'Update your professional credentials and personal information.'}
                {activeTab === 'security' && 'Manage your account security and authentication settings.'}
                {activeTab === 'appearance' && 'Customize the visual experience for maximum comfort.'}
              </p>
            </div>
            <button 
              onClick={onClose}
              className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-muted transition-colors text-text-muted hover:text-text-primary"
            >
              <X className="w-6 h-6" />
            </button>
          </header>

          <div className="flex-1 overflow-y-auto px-8 py-4 space-y-8 pb-12">
            {activeTab === 'profile' && <ProfileTab />}
            {activeTab === 'security' && (
              <SecurityTab 
                twoFactor={security.twoFactor} 
                onToggle2FA={() => setSecurity(s => ({ ...s, twoFactor: !s.twoFactor }))} 
              />
            )}
            {activeTab === 'appearance' && (
              <AppearanceTab 
                fontSize={fontSize}
                setFontSize={setFontSize}
                accentColor={accentColor}
                setAccentColor={setAccentColor}
              />
            )}
          </div>

          {/* Footer Buttons */}
          <footer className="px-8 py-6 border-t border-border flex justify-end gap-4 shrink-0 bg-surface/80 backdrop-blur-sm">
            <button 
              onClick={onClose}
              className="px-8 py-2.5 bg-white border border-border text-sm font-bold text-text-secondary rounded-xl hover:bg-surface-muted transition-colors"
            >
              CANCEL
            </button>
            <button 
              onClick={onClose}
              className="px-8 py-2.5 bg-[#003594] hover:bg-[#002870] text-white text-sm font-bold rounded-xl transition-colors shadow-xl shadow-primary/20 hover:-translate-y-0.5 active:translate-y-0"
            >
              APPLY CHANGES
            </button>
          </footer>
        </main>
      </div>
    </div>
  );
}
