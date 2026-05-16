import { Bell, Smartphone, Info, LayoutDashboard } from 'lucide-react';
import Toggle from './Toggle';

export default function NotificationsTab({ notifications, onToggle }) {
  const items = [
    { id: 'email', title: 'Email Notifications', desc: 'Receive daily health summaries and refill alerts via email.', icon: Bell },
    { id: 'push', title: 'Push Notifications', desc: 'Get instant alerts on your desktop for new medical messages.', icon: Smartphone },
    { id: 'sound', title: 'Sound Effects', desc: 'Play subtle sounds when receiving new chat messages.', icon: Info },
    { id: 'reports', title: 'Weekly Analytics', desc: 'Share anonymized health data with your assigned specialist.', icon: LayoutDashboard },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {items.map((item) => (
        <div key={item.id} className="flex items-center justify-between p-5 bg-surface-muted/50 rounded-2xl border border-border/50">
          <div className="flex gap-4">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center border border-border/50 shadow-sm">
              <item.icon className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-text-primary">{item.title}</h4>
              <p className="text-xs text-text-muted mt-1 leading-relaxed">{item.desc}</p>
            </div>
          </div>
          <Toggle 
            active={notifications[item.id]} 
            onToggle={() => onToggle(item.id)} 
          />
        </div>
      ))}
    </div>
  );
}
