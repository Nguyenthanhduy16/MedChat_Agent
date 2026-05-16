import QuickStats from '../../features/dashboard/components/QuickStats';
import HealthProfileCard from '../../features/dashboard/components/HealthProfileCard';
import MedicationList from '../../features/dashboard/components/MedicationList';
import { Phone } from 'lucide-react';

export default function RightPanel() {
  return (
    <aside className="w-[var(--width-right-panel)] bg-surface border-l border-border flex flex-col h-full shrink-0 overflow-y-auto">
      <div className="p-4 space-y-5">
        <QuickStats />
        <HealthProfileCard />
        <MedicationList />

        {/* CTA Widget */}
        <div className="bg-primary rounded-xl p-4 text-white">
          <div className="flex items-center gap-2 mb-2">
            <Phone className="w-4 h-4" />
            <span className="text-sm font-semibold">Speak with a Licensed</span>
          </div>
          <p className="text-xs text-white/80 leading-relaxed">
            Connect with a healthcare professional for personalized medical advice.
          </p>
          <button className="mt-3 w-full h-9 bg-white text-primary text-sm font-semibold rounded-lg hover:bg-white/90 transition-colors">
            Schedule Call
          </button>
        </div>
      </div>
    </aside>
  );
}
