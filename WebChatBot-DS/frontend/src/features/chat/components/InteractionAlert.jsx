import React from 'react';
import { AlertCircle, X } from 'lucide-react';

export default function InteractionAlert({
  title = 'Interaction Alert:',
  message = '',
  severity = 'warning', // 'warning', 'danger', 'info'
  timestamp = '',
  dismissible = true,
  onDismiss = () => {},
}) {
  const [visible, setVisible] = React.useState(true);

  const handleDismiss = () => {
    setVisible(false);
    onDismiss();
  };

  if (!visible) return null;

  const colorMap = {
    warning: {
      bg: 'bg-yellow-50',
      border: 'border-l-yellow-400',
      title: 'text-slate-900',
      icon: 'text-yellow-600',
    },
    danger: {
      bg: 'bg-red-50',
      border: 'border-l-red-500',
      title: 'text-red-900',
      icon: 'text-red-600',
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-l-blue-500',
      title: 'text-slate-900',
      icon: 'text-blue-600',
    },
  };

  const colors = colorMap[severity] || colorMap.warning;

  return (
    <div className={`flex gap-3 mb-6 group`}>
      {/* Icon Container */}
      <div className="flex-shrink-0 mt-1">
        <div className={`${colors.bg} p-2 rounded-lg`}>
          <AlertCircle size={20} className={colors.icon} />
        </div>
      </div>

      {/* Content Container */}
      <div className={`flex-1 ${colors.bg} border-l-4 ${colors.border} rounded-r-2xl px-4 py-4 shadow-sm relative`}>
        <div className="text-slate-900 text-sm leading-relaxed">
          <p>
            <strong className={colors.title}>{title}</strong>{' '}
            <span className="font-normal text-slate-700">{message}</span>
          </p>
        </div>

        {/* Timestamp */}
        {timestamp && (
          <div className="mt-2">
            <p className="text-xs text-slate-500">{timestamp}</p>
          </div>
        )}

        {/* Dismiss Button */}
        {dismissible && (
          <button
            onClick={handleDismiss}
            className="absolute top-3 right-3 p-1 hover:bg-white/50 rounded transition opacity-0 group-hover:opacity-100"
            title="Dismiss"
          >
            <X size={16} className="text-slate-500" />
          </button>
        )}
      </div>
    </div>
  );
}
