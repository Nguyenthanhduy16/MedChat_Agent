import { Check } from 'lucide-react';
import { cn } from '../../../../utils/cn';
import { useTheme } from '../../../../context/ThemeContext';

export default function AppearanceTab({ 
  fontSize, 
  setFontSize, 
  accentColor, 
  setAccentColor 
}) {
  const { theme, setTheme } = useTheme();
  const colors = [
    { id: 'blue', label: 'Blue', class: 'bg-primary' },
    { id: 'teal', label: 'Soothing Teal', class: 'bg-[#0D9488]' },
    { id: 'green', label: 'Wellness Green', class: 'bg-[#15803D]' },
  ];

  return (
    <div className="space-y-10 animate-fade-in">
      {/* Interface Theme */}
      <section>
        <h3 className="text-base font-bold text-text-primary mb-4">Interface Theme</h3>
        <div className="grid grid-cols-2 gap-4">
          {/* Light Mode */}
          <button 
            onClick={() => setTheme('light')}
            className={cn(
              "text-left rounded-2xl border-2 transition-all p-1 overflow-hidden group relative bg-white shadow-sm",
              theme === 'light' ? "border-primary ring-4 ring-primary/5" : "border-border hover:border-text-muted"
            )}
          >
            <div className="bg-[#F8FAFC] rounded-xl h-24 mb-3 border border-border/50 relative p-3">
                <div className="w-3/4 h-2 bg-slate-200 rounded-full mb-2"></div>
                <div className="w-1/2 h-2 bg-slate-200 rounded-full mb-4 opacity-50"></div>
                <div className="absolute bottom-2 right-2 w-8 h-4 bg-primary rounded-md shadow-sm"></div>
            </div>
            <div className="px-3 pb-3">
              <p className="text-sm font-bold text-text-primary">Clinical Light</p>
              <p className="text-[10px] text-text-muted mt-0.5 font-medium">Clarity for high-focus environments</p>
            </div>
            {theme === 'light' && (
              <div className="absolute top-3 right-3 w-5 h-5 bg-primary text-white rounded-full flex items-center justify-center shadow-sm animate-scale-in">
                <Check className="w-3 h-3" />
              </div>
            )}
          </button>

          {/* Dark Mode */}
          <button 
            onClick={() => setTheme('dark')}
            className={cn(
              "text-left rounded-2xl border-2 transition-all p-1 overflow-hidden group relative bg-white shadow-sm",
              theme === 'dark' ? "border-primary ring-4 ring-primary/5" : "border-border hover:border-text-muted"
            )}
          >
            <div className="bg-[#0F172A] rounded-xl h-24 mb-3 border border-white/5 relative p-3">
                <div className="w-3/4 h-2 bg-slate-700 rounded-full mb-2"></div>
                <div className="w-1/2 h-2 bg-slate-800 rounded-full mb-4 opacity-50"></div>
                <div className="absolute bottom-2 right-2 w-8 h-4 bg-blue-600 rounded-md shadow-sm"></div>
            </div>
            <div className="px-3 pb-3">
              <p className="text-sm font-bold text-text-primary">Midnight Precision</p>
              <p className="text-[10px] text-text-muted mt-0.5 font-medium">Reduced eye strain for clinical shifts</p>
            </div>
            {theme === 'dark' && (
              <div className="absolute top-3 right-3 w-5 h-5 bg-primary text-white rounded-full flex items-center justify-center shadow-sm animate-scale-in">
                <Check className="w-3 h-3" />
              </div>
            )}
          </button>
        </div>
      </section>

      {/* Accessibility Font Size */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-base font-bold text-text-primary">Accessibility Font Size</h3>
          <span className="px-3 py-1 bg-surface-muted rounded-full text-[10px] font-bold text-text-muted border border-border">SYSTEM DEFAULT</span>
        </div>
        <div className="bg-surface-muted/50 rounded-2xl p-8 border border-border/50 relative group">
          <div className="relative h-1.5 w-full bg-slate-200 rounded-full mb-6">
            <div 
              className="absolute h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${fontSize}%` }}
            ></div>
            <input 
              type="range"
              min="0"
              max="100"
              value={fontSize}
              onChange={(e) => setFontSize(e.target.value)}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            />
            <div 
              className="absolute top-1/2 -translate-y-1/2 w-5 h-5 bg-primary border-4 border-white rounded-full shadow-lg pointer-events-none transition-all duration-300 hover:scale-125"
              style={{ left: `calc(${fontSize}% - 10px)` }}
            ></div>
          </div>
          <div className="flex justify-between items-center text-[10px] font-extrabold text-text-muted tracking-widest uppercase">
            <span>Aa</span>
            <span className="text-primary font-black">Aa</span>
            <span className="text-lg">Aa</span>
          </div>
        </div>
      </section>

      {/* Clinical Accent Color */}
      <section>
        <h3 className="text-base font-bold text-text-primary mb-4">Clinical Accent Color</h3>
        <div className="flex gap-4">
          {colors.map((color) => (
            <button
              key={color.id}
              onClick={() => setAccentColor(color.id)}
              className={cn(
                "flex items-center gap-2.5 px-5 py-3 rounded-2xl border-2 transition-all",
                accentColor === color.id 
                  ? "border-primary bg-white shadow-md ring-4 ring-primary/5" 
                  : "border-border bg-surface-muted hover:border-text-muted"
              )}
            >
              <div className={cn("w-4 h-4 rounded-full shadow-inner", color.class)}></div>
              <span className="text-sm font-bold text-text-primary">{color.label}</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
