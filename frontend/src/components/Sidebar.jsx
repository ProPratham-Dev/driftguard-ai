import React from 'react';
import {
  LayoutDashboard,
  Layers,
  Radio,
  Cpu,
  Zap,
  History,
  X,
  ShieldAlert
} from 'lucide-react';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'simulator', label: 'Simulator Controls', icon: Zap },
  { id: 'models', label: 'Model Comparison', icon: Cpu },
  { id: 'drift', label: 'Drift Monitor', icon: Radio },
  { id: 'transactions', label: 'Live Transactions', icon: Layers },
  { id: 'audit', label: 'Model Governance', icon: History },
];

export default function Sidebar({ activeSection, setActiveSection, isOpen, onClose }) {
  const handleNavClick = (id) => {
    setActiveSection(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    if (onClose) onClose();
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden backdrop-blur-xs transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-50 h-screen w-64 bg-sidebar border-r border-theme flex flex-col justify-between transition-transform duration-200 ease-in-out shrink-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div>
          {/* Top Branding */}
          <div className="h-16 px-5 border-b border-theme flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
                <ShieldAlert className="w-5 h-5 text-accent-theme" />
              </div>
              <div>
                <span className="font-bold text-sm tracking-wider text-primary">DRIFTGUARD</span>
                <span className="text-[10px] block font-mono text-secondary">NEUROFORGE 2026</span>
              </div>
            </div>

            {/* Close button for mobile */}
            <button
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-md hover:bg-card-subtle text-secondary cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all text-left cursor-pointer ${
                    isActive
                      ? 'bg-card-subtle text-primary border border-theme font-semibold shadow-xs'
                      : 'text-secondary hover:text-primary hover:bg-card-subtle/50'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-accent-theme' : 'text-muted-custom'
                    }`}
                  />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer info */}
        <div className="p-4 border-t border-theme text-[11px] font-mono text-secondary">
          <div className="flex items-center justify-between">
            <span>Core Engine:</span>
            <span className="text-primary font-bold">ASW-DD + SGD</span>
          </div>
          <div className="flex items-center justify-between mt-1">
            <span>Evaluation:</span>
            <span className="text-accent-theme font-bold">Prequential</span>
          </div>
        </div>
      </aside>
    </>
  );
}
