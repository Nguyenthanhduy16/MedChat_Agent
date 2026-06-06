import { X, Globe } from 'lucide-react';
import { cn } from '../../../utils/cn';

export default function SourcesSidebar({ sources, onClose, isOpen }) {
  // Parsing logic for backward compatibility in case sources is a string
  let displaySources = sources;
  if (typeof sources === 'string') {
    displaySources = [];
    // Regex to match: [1] Sốt xuất huyết - https://www.pharmacity.vn/...
    const sourceRegex = /\[\d+\]\s+(.*?)(?:\s+-\s+(http[^\s]+))?/g;
    let match;
    while ((match = sourceRegex.exec(sources)) !== null) {
      displaySources.push({
        title: match[1],
        url: match[2] || ''
      });
    }
  }

  return (
    <div className={cn(
      "fixed inset-y-0 right-0 w-80 bg-surface border-l border-border shadow-2xl transform transition-transform duration-300 z-50 flex flex-col",
      isOpen ? "translate-x-0" : "translate-x-full"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <h3 className="text-base font-semibold text-text-primary">
          Nguồn {displaySources?.length > 0 && <span className="text-text-muted text-sm ml-1 font-normal">· {displaySources.length}</span>}
        </h3>
        <button 
          onClick={onClose}
          className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {displaySources && displaySources.length > 0 ? (
          displaySources.map((source, index) => {
            let domain = "Nguồn";
            try {
              if (source.url) {
                domain = new URL(source.url).hostname.replace('www.', '');
              }
            } catch (e) {}

            return (
              <div key={index} className="flex flex-col gap-1.5 group p-3 rounded-xl border border-border bg-surface hover:bg-surface-hover transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Globe className="w-3 h-3 text-primary" />
                  </div>
                  <span className="text-[11px] font-bold text-text-secondary truncate uppercase tracking-wider">
                    {domain}
                  </span>
                </div>
                <a 
                  href={source.url || '#'} 
                  target={source.url ? "_blank" : "_self"} 
                  rel="noopener noreferrer"
                  className="text-[14px] font-bold text-text-primary hover:text-primary transition-colors line-clamp-2 leading-snug"
                >
                  {source.title || `Nguồn ${index + 1}`}
                </a>
                {source.snippet && (
                  <p className="text-[12px] text-text-secondary line-clamp-2 mt-0.5 leading-relaxed">
                    {source.snippet}
                  </p>
                )}
              </div>
            );
          })
        ) : (
          <p className="text-sm text-text-muted text-center py-8">Không có nguồn nào.</p>
        )}
      </div>
    </div>
  );
}
