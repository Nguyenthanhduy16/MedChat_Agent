import React from 'react';
import { Search, Bell, ShoppingCart, Menu } from 'lucide-react';

export default function TopBar() {
  return (
    <div className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-10">
      {/* Left Section: Title and Status */}
      <div className="flex items-center gap-4 flex-1">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Flu Symptom Assessment</h2>
          <p className="text-xs text-slate-500 mt-0.5">Dr. Sarah (AI Specialist) is reviewing your inputs</p>
        </div>
      </div>

      {/* Tabs (optional - for navigation) */}
      <div className="flex items-center gap-6 mx-8">
        <button className="text-sm font-medium text-slate-600 hover:text-slate-900 pb-2 border-b-2 border-transparent">
          Dashboard
        </button>
        <button className="text-sm font-medium text-slate-600 hover:text-slate-900 pb-2 border-b-2 border-transparent">
          Prescriptions
        </button>
        <button className="text-sm font-medium text-blue-600 pb-2 border-b-2 border-blue-600">
          Messages
        </button>
      </div>

      {/* Right Section: Search and Icons */}
      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative hidden md:flex">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search medical records..."
            className="pl-10 pr-4 py-2 rounded-lg bg-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Icons */}
        <button className="p-2 hover:bg-slate-100 rounded-lg transition">
          <Bell size={20} className="text-slate-600" />
        </button>
        <button className="p-2 hover:bg-slate-100 rounded-lg transition">
          <ShoppingCart size={20} className="text-slate-600" />
        </button>

        {/* AI Agent Avatar */}
        <div className="flex items-center gap-2 pl-4 border-l border-slate-200">
          <div className="relative">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">AI</span>
            </div>
            <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-white" />
          </div>
        </div>
      </div>
    </div>
  );
}
