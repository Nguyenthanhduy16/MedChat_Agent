export default function AssistantCard({ card }) {
  if (card.type === "treatment") {
    return (
      <div className="bg-surface border border-border rounded-xl overflow-hidden shadow-sm animate-fade-in max-w-[70%]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-3 pb-2">
          <span className="text-xs font-bold text-primary uppercase tracking-wider">
            Recommended Treatment
          </span>
          <span className="text-[10px] font-semibold text-danger bg-danger-soft px-2 py-0.5 rounded-full uppercase">
            Requires RX
          </span>
        </div>

        {/* Drug Name */}
        <div className="px-4 pb-3">
          <h4 className="text-base font-semibold text-text-primary">
            {card.drugName}
          </h4>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-2 border-t border-border">
          <div className="px-4 py-3 border-r border-border">
            <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-0.5">
              Dosage
            </p>
            <p className="text-sm font-semibold text-text-primary">
              {card.dosage}
            </p>
          </div>
          <div className="px-4 py-3">
            <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-0.5">
              Duration
            </p>
            <p className="text-sm font-semibold text-text-primary">
              {card.duration}
            </p>
          </div>
        </div>

        {/* CTA Button */}
        <div className="p-3 pt-0">
          <button className="w-full h-10 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-lg transition-colors">
            Request Prescription Refill
          </button>
        </div>
      </div>
    );
  }

  if (card.type === "alert") {
    return (
      <div className="flex gap-3 animate-fade-in max-w-[70%]">
        <div className="w-8 h-8 bg-surface-muted border border-border rounded-full flex items-center justify-center shrink-0 mt-1">
          <span className="text-sm">⚠️</span>
        </div>
        <div className="bg-surface border-l-3 border-warning rounded-xl rounded-l-none px-4 py-3 shadow-sm">
          <p className="text-sm font-semibold text-text-primary mb-1">
            Interaction Alert:
          </p>
          <p className="text-sm text-text-secondary leading-relaxed">
            {card.content}
          </p>
        </div>
      </div>
    );
  }

  return null;
}
