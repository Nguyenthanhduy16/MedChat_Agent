export default function HealthProfileCard() {
  return (
    <div>
      <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-3">
        Current Health Profile
      </h3>
      <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
        {/* Profile Details */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-[10px] font-medium text-text-muted uppercase tracking-wider">
              Age / Gender
            </p>
            <p className="text-sm font-semibold text-text-primary">42 / Male</p>
          </div>
          <div>
            <p className="text-[10px] font-medium text-text-muted uppercase tracking-wider">
              Weight
            </p>
            <p className="text-sm font-semibold text-text-primary">
              185 <span className="text-text-muted font-normal">lbs</span>
            </p>
          </div>
          <div className="col-span-2">
            <p className="text-[10px] font-medium text-text-muted uppercase tracking-wider">
              Blood Type
            </p>
            <p className="text-sm font-semibold text-text-primary">
              A+ <span className="text-primary font-semibold">Positive</span>
            </p>
          </div>
        </div>

        {/* Allergies */}
        <div>
          <p className="text-[10px] font-medium text-text-muted uppercase tracking-wider mb-2">
            Known Allergies
          </p>
          <div className="flex flex-wrap gap-1.5">
            <span className="text-[10px] font-bold text-danger bg-danger-soft px-2 py-1 rounded-md uppercase tracking-wider">
              Penicillin
            </span>
            <span className="text-[10px] font-bold text-warning bg-warning-soft px-2 py-1 rounded-md uppercase tracking-wider">
              Latex
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
