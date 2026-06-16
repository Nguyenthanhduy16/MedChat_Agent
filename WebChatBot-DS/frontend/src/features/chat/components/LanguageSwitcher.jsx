import { Languages } from 'lucide-react';
import { useLanguage } from '../../../context/LanguageContext';
import { cn } from '../../../utils/cn';

export default function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();

  const langs = [
    { code: 'EN', label: 'EN' },
    { code: 'VN', label: 'VN' },
    { code: 'JP', label: 'JP' },
  ];

  return (
    <div className="flex items-center bg-surface-muted border border-border rounded-lg p-1">
      <Languages className="w-4 h-4 text-text-muted mx-2" />
      <div className="flex gap-1">
        {langs.map((lang) => (
          <button 
            key={lang.code}
            onClick={() => setLanguage(lang.code)}
            className={cn(
              "px-2 py-1 text-[10px] font-bold rounded-md transition-all",
              language === lang.code ? "bg-primary text-white shadow-sm" : "text-text-muted hover:text-text-primary"
            )}
          >
            {lang.label}
          </button>
        ))}
      </div>
    </div>
  );
}
