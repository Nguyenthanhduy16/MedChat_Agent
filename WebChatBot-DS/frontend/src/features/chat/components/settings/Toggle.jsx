import { cn } from '../../../../utils/cn';

export default function Toggle({ active, onToggle }) {
  return (
    <button 
      onClick={onToggle}
      className={cn(
        "w-11 h-6 rounded-full transition-colors relative flex items-center px-1",
        active ? "bg-primary" : "bg-slate-200"
      )}
    >
      <div className={cn(
        "w-4 h-4 bg-white rounded-full shadow-sm transition-transform",
        active ? "translate-x-5" : "translate-x-0"
      )} />
    </button>
  );
}
