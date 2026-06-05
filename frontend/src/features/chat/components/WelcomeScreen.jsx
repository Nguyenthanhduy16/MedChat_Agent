import { useLanguage } from '../../../context/LanguageContext';
import { Bot, Activity, Pill, ShieldAlert, HeartPulse } from 'lucide-react';

export default function WelcomeScreen({ onSelectSuggestion }) {
  const { t } = useLanguage();

  const suggestions = [
    { text: "Thuốc Paracetamol có tác dụng gì?", icon: Pill },
    { text: "Tôi bị đau đầu và sốt nhẹ, nên làm gì?", icon: Activity },
    { text: "Cách phòng ngừa cảm cúm mùa hiệu quả?", icon: ShieldAlert },
    { text: "Chỉ số huyết áp 120/80 có tốt không?", icon: HeartPulse },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 text-center animate-fade-in w-full max-w-3xl mx-auto">
      <div className="w-20 h-20 rounded-full flex items-center justify-center mb-6 overflow-hidden shadow-sm border border-border bg-white">
        <img src="/logo.png" alt="MedChat Logo" className="w-full h-full object-cover" />
      </div>
      
      <h2 className="text-2xl font-semibold text-text-primary mb-3">
        Hôm nay bạn cần hỗ trợ gì?
      </h2>
      <p className="text-sm text-text-secondary max-w-md mb-12">
        Tôi có thể giúp bạn tra cứu thông tin thuốc, tư vấn triệu chứng ban đầu hoặc phân tích dữ liệu sức khỏe.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
        {suggestions.map((item, i) => {
          const Icon = item.icon;
          return (
            <button
              key={i}
              onClick={() => onSelectSuggestion(item.text)}
              className="flex items-start gap-3 p-4 bg-white border border-border rounded-xl text-left hover:bg-surface-hover transition-colors"
            >
              <Icon className="w-5 h-5 text-text-muted shrink-0 mt-0.5" />
              <span className="text-sm text-text-primary leading-relaxed">
                {item.text}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
