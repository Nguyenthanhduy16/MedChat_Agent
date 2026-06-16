import React, { useState } from 'react';

export default function TreatmentCard({
  medicationName = 'Oseltamivir (Tamiflu)',
  dosage = '75mg Twice Daily',
  duration = '5 Days',
  requiresRx = true,
  action = 'Request Prescription Refill',
  onAction = () => {},
  notes = '',
}) {
  const [isLoading, setIsLoading] = useState(false);

  const handleAction = async () => {
    setIsLoading(true);
    try {
      await onAction();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm mb-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-bold text-teal-700 tracking-wider uppercase">
              Recommended Treatment
            </span>
          </div>
          <h3 className="text-lg font-semibold text-slate-900">{medicationName}</h3>
        </div>
        {requiresRx && (
          <div className="bg-red-50 px-2 py-1 rounded">
            <span className="text-xs font-bold text-red-600 tracking-wider uppercase">
              Requires RX
            </span>
          </div>
        )}
      </div>

      {/* Dosage and Duration Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* Dosage */}
        <div className="bg-slate-50 rounded-xl p-3">
          <p className="text-xs font-bold text-slate-500 uppercase mb-1">Dosage</p>
          <p className="text-sm font-semibold text-slate-900">{dosage}</p>
        </div>

        {/* Duration */}
        <div className="bg-slate-50 rounded-xl p-3">
          <p className="text-xs font-bold text-slate-500 uppercase mb-1">Duration</p>
          <p className="text-sm font-semibold text-slate-900">{duration}</p>
        </div>
      </div>

      {/* Notes */}
      {notes && (
        <div className="bg-blue-50 rounded-lg p-3 mb-4 border-l-4 border-blue-500">
          <p className="text-sm text-slate-700">{notes}</p>
        </div>
      )}

      {/* Action Button */}
      <button
        onClick={handleAction}
        disabled={isLoading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white font-semibold py-2.5 rounded-lg transition shadow-lg hover:shadow-xl"
      >
        {isLoading ? 'Processing...' : action}
      </button>
    </div>
  );
}
