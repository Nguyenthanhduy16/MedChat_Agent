import { Pill, Link2 } from 'lucide-react';

const medications = [
  {
    id: 1,
    name: 'Lisinopril',
    detail: '10mg Oral Tablet',
    status: 'Taken Today',
    statusColor: 'text-success',
  },
  {
    id: 2,
    name: 'Metformin',
    detail: '500mg Extended Release',
    status: 'Due in 2H',
    statusColor: 'text-danger',
  },
];

export default function MedicationList() {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
          Active Medications
        </h3>
        <button className="text-[11px] font-semibold text-primary hover:text-primary-dark transition-colors uppercase tracking-wider">
          View All
        </button>
      </div>
      <div className="space-y-2">
        {medications.map((med) => (
          <div
            key={med.id}
            className="bg-surface border border-border rounded-xl p-3 flex items-start gap-3"
          >
            <div className="w-8 h-8 bg-primary-soft rounded-lg flex items-center justify-center shrink-0 mt-0.5">
              <Pill className="w-4 h-4 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <Link2 className="w-3 h-3 text-text-muted shrink-0" />
                <p className="text-sm font-semibold text-text-primary truncate">
                  {med.name}
                </p>
              </div>
              <p className="text-xs text-text-muted mt-0.5">{med.detail}</p>
              <p className={`text-[10px] font-bold uppercase tracking-wider mt-1 ${med.statusColor}`}>
                {med.status}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
