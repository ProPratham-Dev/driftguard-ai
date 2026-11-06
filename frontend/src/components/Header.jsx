import React from 'react';
import {
  ShieldAlert,
  Wifi,
  WifiOff,
  Zap,
  Sun,
  Moon,
  Menu
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function Header({ isConnected, simulatorStatus, onOpenMobileMenu }) {
  const { theme, toggleTheme, isDark } = useTheme();

  const isRunning = simulatorStatus?.is_running;
  const isPaused = simulatorStatus?.is_paused;
  const regime = simulatorStatus?.fraud_regime || 'normal';

  return (
    <header className="h-16 px-4 sm:px-6 bg-card border-b border-theme sticky top-0 z-30 flex items-center justify-between transition-colors duration-200">
      
      {/* Left: Mobile Menu Toggle & Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-2 rounded-lg text-secondary hover:bg-card-subtle cursor-pointer"
          title="Open Navigation Menu"
        >
          <Menu className="w-5 h-5 text-primary" />
        </button>

        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-accent-theme">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-wide text-primary flex items-center gap-1.5">
              DRIFT<span className="text-accent-theme">GUARD</span>
              <span className="hidden sm:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-card-subtle text-secondary border border-theme">
                AI v1.0
              </span>
            </h1>
          </div>
        </div>
      </div>

      {/* Right: Badges & Controls */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        
        {/* Active Fraud Regime Badge */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-card-subtle border border-theme text-xs font-mono">
          <span className="text-secondary text-[11px]">Regime:</span>
          {regime === 'normal' && (
            <span className="text-emerald-500 dark:text-emerald-400 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Normal
            </span>
          )}
          {regime === 'historical' && (
            <span className="text-amber-500 dark:text-amber-400 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Historical
            </span>
          )}
          {regime === 'drift_evasion' && (
            <span className="text-accent-theme font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse"></span> Changed Strategy
            </span>
          )}
        </div>

        {/* Engine Status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-card-subtle border border-theme text-xs font-mono">
          <Zap className={`w-3.5 h-3.5 ${isRunning ? (isPaused ? 'text-amber-500' : 'text-accent-theme animate-pulse') : 'text-muted-custom'}`} />
          <span className="hidden sm:inline text-secondary text-[11px]">Simulator:</span>
          <span className={`font-semibold text-[11px] ${isRunning ? (isPaused ? 'text-amber-500' : 'text-accent-theme') : 'text-secondary'}`}>
            {isRunning ? (isPaused ? 'PAUSED' : 'STREAMING') : 'IDLE'}
          </span>
        </div>

        {/* WebSocket Indicator */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-mono transition-colors ${
          isConnected
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
            : 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
        }`}>
          {isConnected ? <Wifi className="w-3.5 h-3.5 animate-pulse" /> : <WifiOff className="w-3.5 h-3.5" />}
          <span className="hidden sm:inline text-[11px]">{isConnected ? 'LIVE' : 'OFFLINE'}</span>
        </div>

        {/* Theme Switcher Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg bg-card-subtle hover:bg-theme-card-hover border border-theme text-primary transition-all cursor-pointer flex items-center justify-center"
          title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
          aria-label="Toggle Theme"
        >
          {isDark ? (
            <Sun className="w-4 h-4 text-amber-400 hover:rotate-45 transition-transform" />
          ) : (
            <Moon className="w-4 h-4 text-slate-700 hover:-rotate-12 transition-transform" />
          )}
        </button>

      </div>
    </header>
  );
}
