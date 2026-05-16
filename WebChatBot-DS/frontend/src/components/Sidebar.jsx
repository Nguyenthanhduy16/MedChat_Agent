import React, { useState } from 'react';
import { Plus, MessageSquare, Settings, HelpCircle, ClipboardList, Clock, Bell } from 'lucide-react';

export default function Sidebar() {
  const [activeThread, setActiveThread] = useState('consultation-1');

  return (
    <div className="w-64 h-screen bg-white border-r border-slate-200 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-slate-200">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">PC</span>
          </div>
          <h1 className="text-lg font-bold text-slate-900">PharmaCare</h1>
        </div>
        <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg flex items-center justify-center gap-2 transition">
          <Plus size={18} />
          Start Consultation
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Active Threads */}
        <div className="p-4">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Active Threads</h3>
          <div className="space-y-2">
            {[
              { id: 'consultation-1', name: 'Consultations', icon: MessageSquare },
              { id: 'prescriptions', name: 'Prescriptions', icon: ClipboardList },
              { id: 'order-history', name: 'Order History', icon: Clock },
              { id: 'reminders', name: 'Reminders', icon: Bell },
            ].map(({ id, name, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveThread(id)}
                className={`w-full text-left px-3 py-2 rounded-lg transition flex items-center gap-3 ${
                  activeThread === id
                    ? 'bg-blue-100 text-blue-600'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Icon size={18} />
                <span className="text-sm font-medium">{name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Categories */}
        <div className="px-4 py-3 border-t border-slate-200">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Categories</h3>
          <div className="space-y-2">
            {[
              { name: 'Flu & Cold', color: 'bg-blue-100', dot: 'bg-blue-600' },
              { name: 'Pain Relief', color: 'bg-orange-100', dot: 'bg-orange-600' },
              { name: 'Skin Care', color: 'bg-pink-100', dot: 'bg-pink-600' },
            ].map(({ name, color, dot }) => (
              <button key={name} className={`w-full text-left px-3 py-2 rounded-lg ${color} text-slate-700 hover:opacity-80 transition flex items-center gap-3`}>
                <span className={`w-2 h-2 rounded-full ${dot}`} />
                <span className="text-sm font-medium">{name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-slate-200 space-y-2">
        <button className="w-full text-left px-3 py-2 rounded-lg text-slate-600 hover:bg-slate-100 transition flex items-center gap-3">
          <Settings size={18} />
          <span className="text-sm font-medium">Settings</span>
        </button>
        <button className="w-full text-left px-3 py-2 rounded-lg text-slate-600 hover:bg-slate-100 transition flex items-center gap-3">
          <HelpCircle size={18} />
          <span className="text-sm font-medium">Support</span>
        </button>
      </div>
    </div>
  );
}
