import { useLanguage } from '../../../context/LanguageContext';
import { Bot, MessageSquare, Pill, BarChart3, ShieldCheck } from 'lucide-react';

export default function WelcomeScreen({ onSelectSuggestion }) {
  const { t } = useLanguage();

  const suggestions = [
    { text: t('suggestion1'), icon: Pill },
    { text: t('suggestion2'), icon: ShieldCheck },
    { text: t('suggestion3'), icon: BarChart3 },
    { text: t('suggestion4'), icon: MessageSquare },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center animate-fade-in">
      <div className="w-16 h-16 bg-primary-soft rounded-2xl flex items-center justify-center mb-6 shadow-sm">
        <Bot className="w-10 h-10 text-primary" />
      </div>
      
      <h2 className="text-2xl font-bold text-text-primary mb-2">
        {t('welcomeTitle')}
      </h2>
      <p className="text-text-secondary max-w-md mb-10 leading-relaxed">
        {t('welcomeSubtitle')}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
        {suggestions.map((item, i) => {
          const Icon = item.icon;
          return (
            <button
              key={i}
              onClick={() => onSelectSuggestion(item.text)}
              className="flex items-center gap-3 px-4 py-3 bg-surface border border-border rounded-xl text-left hover:border-primary hover:bg-primary-soft group transition-all"
            >
              <div className="w-8 h-8 bg-surface-muted group-hover:bg-surface rounded-lg flex items-center justify-center shrink-0">
                <Icon className="w-4 h-4 text-text-secondary group-hover:text-primary transition-colors" />
              </div>
              <span className="text-sm font-medium text-text-primary group-hover:text-primary transition-colors">
                {item.text}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-12 flex items-center gap-2 text-xs text-text-muted">
        <ShieldCheck className="w-3.5 h-3.5" />
        <span>{t('disclaimer')}</span>
      </div>
    </div>
  );
}
