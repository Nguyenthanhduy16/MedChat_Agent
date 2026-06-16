import { Search, Bell, ShoppingCart, ChevronDown } from 'lucide-react';

const navItems = [
  { label: 'Dashboard', href: '#', active: false },
  { label: 'Prescriptions', href: '#', active: false },
  { label: 'Messages', href: '#', active: true },
];

export default function TopBar() {
  return (
    <header className="h-[var(--height-topbar)] bg-surface border-b border-border flex items-center px-6 gap-6 sticky top-0 z-50">
      {/* Brand */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
          <span className="text-white text-sm font-bold">M</span>
        </div>
        <span className="text-lg font-bold text-primary tracking-tight">
          MedAgent
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex items-center gap-1 ml-4">
        {navItems.map((item) => (
          <a
            key={item.label}
            href={item.href}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              item.active
                ? 'text-primary border-b-2 border-primary'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
            }`}
          >
            {item.label}
          </a>
        ))}
      </nav>

      {/* Search */}
      <div className="flex-1 max-w-md ml-auto">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            placeholder="Search medical records..."
            className="w-full h-9 pl-9 pr-4 bg-surface-muted border border-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        <button className="w-9 h-9 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors relative">
          <Bell className="w-[18px] h-[18px]" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-danger rounded-full"></span>
        </button>
        <button className="w-9 h-9 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors">
          <ShoppingCart className="w-[18px] h-[18px]" />
        </button>
        <div className="w-px h-6 bg-border mx-2"></div>
        <button className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-lg hover:bg-surface-hover transition-colors">
          <div className="w-8 h-8 bg-primary-soft rounded-full flex items-center justify-center">
            <span className="text-xs font-semibold text-primary">TM</span>
          </div>
          <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
        </button>
      </div>
    </header>
  );
}
