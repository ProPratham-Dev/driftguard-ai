import React from 'react';
import { ShieldAlert, Activity, Wifi, WifiOff, Zap } from 'lucide-react';

export default function Header({ isConnected, simulatorStatus }) {
  const isRunning = simulatorStatus?.is_running;
  const isPaused = simulatorStatus?.is_paused;
  const regime = simulatorStatus?.fraud_regime || 'normal';

  return (
    <header className="border-b border-slate-800 bg-[#081024]/90 backdrop-blur sticky top-0 z-50 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-700 shadow-lg shadow-cyan-500/20">
            <ShieldAlert className="w-6 h-6 text-white" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-wider text-white">
                DRIFT<span className="text-cyan-400">GUARD</span> AI
              </h1>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                NeuroForge 2026
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Adaptive Real-Time Fraud & Concept Drift Defense System
            </p>
          </div>
        </div>

        {/* Live Status Indicators */}
        <div className="flex flex-wrap items-center gap-3">
          
          {/* Regime Badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
            <span className="text-slate-400">Regime:</span>
            {regime === 'normal' && (
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Normal Traffic
              </span>
            )}
            {regime === 'historical' && (
              <span className="text-amber-400 font-semibold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-400"></span> Historical Fraud
              </span>
            )}
            {regime === 'drift_evasion' && (
              <span className="text-cyan-400 font-semibold flex items-center gap-1 animate-pulse">
                <span className="w-2 h-2 rounded-full bg-cyan-400"></span> Evasion Attack (Drift)
              </span>
            )}
          </div>

          {/* Simulator Engine Status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
            <Zap className={`w-3.5 h-3.5 ${isRunning ? (isPaused ? 'text-amber-400' : 'text-cyan-400 animate-pulse') : 'text-slate-500'}`} />
            <span className="text-slate-400">Engine:</span>
            <span className={`font-semibold ${isRunning ? (isPaused ? 'text-amber-400' : 'text-cyan-300') : 'text-slate-400'}`}>
              {isRunning ? (isPaused ? 'PAUSED' : 'STREAMING') : 'IDLE'}
            </span>
          </div>

          {/* WebSocket Status */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono ${
            isConnected
              ? 'bg-emerald-950/40 border-emerald-800 text-emerald-400'
              : 'bg-rose-950/40 border-rose-800 text-rose-400'
          }`}>
            {isConnected ? <Wifi className="w-3.5 h-3.5 animate-pulse" /> : <WifiOff className="w-3.5 h-3.5" />}
            <span>{isConnected ? 'LIVE WS CONNECTED' : 'DISCONNECTED'}</span>
          </div>

        </div>

      </div>
    </header>
  );
}
