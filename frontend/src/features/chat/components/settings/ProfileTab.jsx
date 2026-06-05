import { Plus } from 'lucide-react';

export default function ProfileTab() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-6">
        <div className="relative group">
          <div className="w-24 h-24 rounded-3xl overflow-hidden border-2 border-border p-1 bg-white shadow-sm">
            <img 
              src="https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?q=80&w=200&auto=format&fit=crop" 
              alt="Profile"
              className="w-full h-full object-cover rounded-2xl"
            />
          </div>
          <button className="absolute -bottom-2 -right-2 w-8 h-8 bg-primary text-white rounded-xl flex items-center justify-center shadow-lg hover:scale-110 transition-transform">
            <Plus className="w-4 h-4" />
          </button>
        </div>
        <div>
          <h4 className="text-lg font-bold text-text-primary">Alex Chen, M.D.</h4>
          <p className="text-sm text-text-muted">Chief Medical Officer • San Francisco</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-5">
        <div className="space-y-2">
          <label className="text-xs font-bold text-text-muted uppercase tracking-wider">Full Name</label>
          <input type="text" defaultValue="Alex Chen" className="w-full h-11 px-4 bg-surface-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/10" />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-bold text-text-muted uppercase tracking-wider">Professional Title</label>
          <input type="text" defaultValue="Medical Doctor" className="w-full h-11 px-4 bg-surface-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/10" />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-bold text-text-muted uppercase tracking-wider">Email Address</label>
          <input type="email" defaultValue="a.chen@hospital.org" className="w-full h-11 px-4 bg-surface-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/10" />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-bold text-text-muted uppercase tracking-wider">License Number</label>
          <input type="text" defaultValue="MD-9988776655" className="w-full h-11 px-4 bg-surface-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/10" />
        </div>
      </div>
    </div>
  );
}
