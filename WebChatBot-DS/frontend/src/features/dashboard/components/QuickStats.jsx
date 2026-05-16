import { Heart, Activity } from 'lucide-react';

const stats = [
  {
    label: 'Resting HR',
    value: '72',
    unit: 'BPM',
    icon: Heart,
    iconColor: 'text-danger',
    iconBg: 'bg-danger-soft',
  },
  {
    label: 'Blood Pressure',
    value: '128/84',
    unit: '',
    icon: Activity,
    iconColor: 'text-primary',
    iconBg: 'bg-primary-soft',
  },
];

export default function QuickStats() {
  return (
    <div>
      <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-3">
        Quick Stats
      </h3>
      <div className="space-y-2">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="bg-surface border border-border rounded-xl p-3 flex flex-col items-center text-center"
            >
              <p className="text-[10px] font-medium text-text-muted uppercase tracking-wider mb-1.5">
                {stat.label}
              </p>
              <div className={`w-8 h-8 ${stat.iconBg} rounded-lg flex items-center justify-center mb-1.5`}>
                <Icon className={`w-4 h-4 ${stat.iconColor}`} />
              </div>
              <p className="text-xl font-bold text-text-primary leading-none">
                {stat.value}
              </p>
              {stat.unit && (
                <p className="text-[10px] font-medium text-text-muted mt-0.5">
                  {stat.unit}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
