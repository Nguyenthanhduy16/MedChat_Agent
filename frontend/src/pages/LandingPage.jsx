import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import LanguageSwitcher from '../features/chat/components/LanguageSwitcher';
import UserMenu from '../components/ui/UserMenu';
import {
  ArrowRight,
  MessageSquare,
  Shield,
  Truck,
  CheckCircle2,
  Bot,
  ChevronRight
} from 'lucide-react';
import { cn } from '../utils/cn';

export default function LandingPage({ onStartChat, onShowAuth }) {
  const { t } = useLanguage();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      {/* ========== NAV BAR ========== */}
      <header className="h-14 bg-surface border-b border-border flex items-center px-8 sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden bg-white">
            <img src="/logo.png" alt="MedAgent" className="w-full h-full object-cover" />
          </div>
          <span className="text-lg font-bold text-primary tracking-tight">
            MedAgent
          </span>
        </div>
        <nav className="flex items-center gap-1 ml-8">
          <button
            className="px-3 py-1.5 text-sm font-medium text-primary border-b-2 border-primary rounded-md transition-colors"
          >
            {t('dashboard')}
          </button>
          <button
            onClick={onStartChat}
            className="px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-hover rounded-md transition-colors"
          >
            {t('messages')}
          </button>
        </nav>
        <div className="flex-1" />
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          {user ? (
            <UserMenu />
          ) : (
            <>
              <button
                onClick={onShowAuth}
                className="px-4 py-1.5 text-sm font-semibold text-text-primary border border-border rounded-lg hover:bg-surface-hover transition-colors"
              >
                Đăng nhập
              </button>
              <button
                onClick={onShowAuth}
                className="px-4 py-1.5 text-sm font-semibold text-white bg-primary rounded-lg hover:bg-primary-dark transition-colors"
              >
                Đăng ký
              </button>
            </>
          )}
        </div>
      </header>

      {/* ========== HERO SECTION ========== */}
      <section className="bg-surface-muted">
        <div className="max-w-7xl mx-auto px-8 py-16 flex items-center gap-16">
          {/* Left */}
          <div className="flex-1 max-w-lg">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-primary bg-primary-soft px-3 py-1 rounded-full uppercase tracking-wider mb-5">
              <Shield className="w-3.5 h-3.5" />
              Clinically Verified AI
            </span>
            <h1 className="text-4xl md:text-[44px] font-extrabold text-text-primary leading-tight mb-4">
              {t('heroTitle')}
              <span className="text-primary">{t('heroTitleAccent')}</span>
            </h1>
            <p className="text-base text-text-secondary leading-relaxed mb-8 max-w-md">
              {t('heroSubtitle')}
            </p>
            <div className="flex items-center gap-3 mb-8">
              <button
                onClick={onStartChat}
                className="h-11 px-6 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-lg flex items-center gap-2 transition-all shadow-md hover:shadow-lg"
              >
                {t('startConsultation')}
                <ArrowRight className="w-4 h-4" />
              </button>
              <button className="h-11 px-6 bg-surface border border-border text-text-primary text-sm font-semibold rounded-lg hover:bg-surface-hover transition-colors">
                {t('howItWorks')}
              </button>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex -space-x-2">
                {['bg-primary', 'bg-blue-400', 'bg-indigo-500', 'bg-primary-dark'].map(
                  (bg, i) => (
                    <div
                      key={i}
                      className={`w-8 h-8 ${bg} rounded-full border-2 border-surface flex items-center justify-center`}
                    >
                      <span className="text-[10px] font-bold text-white">
                        {['A', 'B', 'C', 'D'][i]}
                      </span>
                    </div>
                  )
                )}
              </div>
              <span className="text-sm text-text-secondary">
                <span className="font-semibold text-text-primary">50,000+</span>{' '}
                {t('trustText')}
              </span>
            </div>
          </div>

          {/* Right — Chat Preview */}
          <div className="flex-1 hidden lg:block">
            <div className="bg-surface rounded-2xl border border-border shadow-panel p-5 max-w-md ml-auto space-y-3">
              {/* Bot message */}
              <div className="flex gap-2.5">
                <div className="w-7 h-7 bg-primary rounded-full flex items-center justify-center shrink-0">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="bg-surface-muted border border-border rounded-xl rounded-bl-sm px-3.5 py-2.5 text-sm text-text-primary max-w-[85%]">
                  Hello! I'm your AI pharmacist. How can I help you today?
                </div>
              </div>
              {/* User message */}
              <div className="flex justify-end">
                <div className="bg-primary rounded-xl rounded-br-sm px-3.5 py-2.5 text-sm text-white max-w-[85%]">
                  I have a headache and need to refill my Ibuprofen.
                </div>
              </div>
              {/* Treatment card mini */}
              <div className="flex gap-2.5">
                <div className="w-7 h-7 bg-primary rounded-full flex items-center justify-center shrink-0">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="bg-surface border border-border rounded-xl overflow-hidden max-w-[85%]">
                  <div className="px-3.5 py-2 flex items-center justify-between">
                    <span className="text-[10px] font-bold text-primary uppercase tracking-wider">
                      Ibuprofen 400mg
                    </span>
                    <span className="text-[9px] font-semibold text-success bg-success-soft px-1.5 py-0.5 rounded-full uppercase">
                      Refill Ready
                    </span>
                  </div>
                  <div className="px-3.5 py-1.5 text-xs text-text-secondary">
                    Your refill request is ready for pick up or home delivery.
                    It should be available within 4 hours.
                  </div>
                  <div className="px-3.5 pb-2.5 pt-1">
                    <button className="w-full h-8 bg-primary text-white text-xs font-semibold rounded-lg">
                      Order Now
                    </button>
                  </div>
                </div>
              </div>
              {/* Bot follow-up */}
              <div className="flex gap-2.5">
                <div className="w-7 h-7 bg-primary rounded-full flex items-center justify-center shrink-0">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="bg-surface-muted border border-border rounded-xl rounded-bl-sm px-3.5 py-2.5 text-sm text-text-primary max-w-[85%]">
                  Refill authorized. Shall I schedule home delivery for you?
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========== FEATURES SECTION ========== */}
      <section className="py-20 bg-surface">
        <div className="max-w-7xl mx-auto px-8 text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-3">
            {t('featuresTitle')}
          </h2>
          <p className="text-text-secondary max-w-xl mx-auto mb-12">
            {t('featuresSubtitle')}
          </p>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {[
              {
                icon: MessageSquare,
                title: t('feature1Title'),
                desc: t('feature1Desc'),
                color: 'text-primary',
                bg: 'bg-primary-soft',
              },
              {
                icon: Shield,
                title: t('feature2Title'),
                desc: t('feature2Desc'),
                color: 'text-success',
                bg: 'bg-success-soft',
              },
              {
                icon: Truck,
                title: t('feature3Title'),
                desc: t('feature3Desc'),
                color: 'text-info',
                bg: 'bg-info-soft',
              },
            ].map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="bg-surface border border-border rounded-2xl p-6 text-left hover:shadow-panel transition-shadow"
                >
                  <div
                    className={`w-12 h-12 ${feature.bg} rounded-xl flex items-center justify-center mb-4`}
                  >
                    <Icon className={`w-6 h-6 ${feature.color}`} />
                  </div>
                  <h3 className="text-base font-semibold text-text-primary mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {feature.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ========== CTA BLUE SECTION ========== */}
      <section className="bg-primary">
        <div className="max-w-7xl mx-auto px-8 py-16 flex items-center gap-16">
          <div className="flex-1 text-white max-w-md">
            <h2 className="text-2xl md:text-3xl font-bold mb-6">
              {t('ctaTitle')}
            </h2>
            <ul className="space-y-3 mb-8">
              {[
                t('ctaItem1'),
                t('ctaItem2'),
                t('ctaItem3'),
              ].map((item) => (
                <li key={item} className="flex items-center gap-2.5 text-sm text-white/90">
                  <CheckCircle2 className="w-4 h-4 text-white shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
            <button
              onClick={onStartChat}
              className="h-11 px-6 bg-white text-primary text-sm font-semibold rounded-lg hover:bg-white/90 transition-colors flex items-center gap-2"
            >
              {t('tryAssistant')}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          {/* Device Mockup */}
          <div className="flex-1 hidden lg:flex justify-center">
            <div className="w-72 h-48 bg-gray-900 rounded-2xl p-3 shadow-2xl relative overflow-hidden">
              <div className="absolute top-3 left-3 right-3 flex items-center gap-1.5">
                <span className="w-2 h-2 bg-red-400 rounded-full"></span>
                <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                <span className="w-2 h-2 bg-green-400 rounded-full"></span>
              </div>
              <div className="mt-6 space-y-2 px-1">
                <div className="h-2 bg-emerald-500/30 rounded w-3/4"></div>
                <div className="h-2 bg-emerald-500/20 rounded w-1/2"></div>
                <div className="h-6 bg-emerald-500/10 rounded-lg mt-3 flex items-center px-2">
                  <div className="h-1.5 bg-emerald-400/50 rounded w-2/3"></div>
                </div>
                <div className="grid grid-cols-3 gap-1.5 mt-2">
                  <div className="h-8 bg-emerald-500/15 rounded-md"></div>
                  <div className="h-8 bg-emerald-500/15 rounded-md"></div>
                  <div className="h-8 bg-emerald-500/15 rounded-md"></div>
                </div>
              </div>
              {/* Notification badge */}
              <div className="absolute -top-1 -right-1 bg-success text-white text-[9px] font-bold px-2 py-0.5 rounded-full shadow-md">
                9:30 AM Tomorrow
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========== BOTTOM CTA ========== */}
      <section className="py-20 bg-surface text-center">
        <div className="max-w-2xl mx-auto px-8">
          <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-3">
            {t('readyTitle')}
          </h2>
          <p className="text-text-secondary mb-8">
            {t('readySubtitle')}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={onStartChat}
              className="h-11 px-6 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-lg transition-all shadow-md hover:shadow-lg"
            >
              {t('getStarted')}
            </button>
            <button className="h-11 px-6 bg-surface border border-border text-text-primary text-sm font-semibold rounded-lg hover:bg-surface-hover transition-colors">
              {t('talkSpecialist')}
            </button>
          </div>
        </div>
      </section>

      {/* ========== FOOTER ========== */}
      <footer className="border-t border-border bg-surface-muted py-6">
        <div className="max-w-7xl mx-auto px-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md flex items-center justify-center overflow-hidden bg-white">
              <img src="/logo.png" alt="MedAgent" className="w-full h-full object-cover" />
            </div>
            <span className="text-sm font-semibold text-text-primary">
              MedAgent
            </span>
          </div>
          <div className="flex items-center gap-6 text-xs text-text-muted">
            <span>© 2024 MedAgent AI. Clinical Excellence in Pharmaceutical Care.</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-text-muted">
            {[t('Privacy Policy'), t('Terms of Service'), t('Contact')].map((link) => (
              <a key={link} href="#" className="hover:text-text-primary transition-colors">
                {link}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
