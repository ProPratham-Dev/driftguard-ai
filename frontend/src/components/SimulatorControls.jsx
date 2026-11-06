import React from 'react';
import { Play, Pause, Square, FastForward, ShieldAlert, Zap, Clock, RotateCcw } from 'lucide-react';

export default function SimulatorControls({
  simulatorStatus,
  startSimulator,
  pauseSimulator,
  resumeSimulator,
  stopSimulator,
  updateConfig
}) {
  const isRunning = simulatorStatus?.is_running;
  const isPaused = simulatorStatus?.is_paused;
  const regime = simulatorStatus?.fraud_regime || 'normal';
  const intervalMs = simulatorStatus?.interval_ms || 500;
  const feedbackDelayMs = simulatorStatus?.feedback_delay_ms || 3000;
  const adaptiveEnabled = simulatorStatus?.adaptive_learning_enabled ?? true;

  return (
    <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-5 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-3">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-cyan-400" />
            Hackathon Demonstration Controls
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Demonstrate real-time concept drift detection and online model adaptation.
          </p>
        </div>

        {/* Engine State Controls */}
        <div className="flex items-center gap-2">
          {!isRunning ? (
            <button
              onClick={startSimulator}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-600/30 transition-all cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-white" /> Start Stream
            </button>
          ) : isPaused ? (
            <button
              onClick={resumeSimulator}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-white" /> Resume
            </button>
          ) : (
            <button
              onClick={pauseSimulator}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition-all cursor-pointer"
            >
              <Pause className="w-3.5 h-3.5 fill-white" /> Pause
            </button>
          )}

          {isRunning && (
            <button
              onClick={stopSimulator}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-rose-900/60 hover:bg-rose-800 border border-rose-700 text-rose-300 text-xs font-semibold transition-all cursor-pointer"
            >
              <Square className="w-3.5 h-3.5 fill-rose-300" /> Stop
            </button>
          )}
        </div>
      </div>

      {/* 3 Main Hackathon Demonstration Buttons */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
        
        {/* Control 1: Normal Traffic */}
        <button
          onClick={() => {
            updateConfig({ fraud_regime: 'normal' });
            if (!isRunning) startSimulator();
          }}
          className={`flex flex-col p-3 rounded-lg border text-left transition-all cursor-pointer ${
            regime === 'normal'
              ? 'bg-emerald-950/40 border-emerald-500/80 shadow-lg shadow-emerald-950/50'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-white uppercase tracking-wider">1. Start Normal Traffic</span>
            <span className={`w-2.5 h-2.5 rounded-full ${regime === 'normal' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-700'}`}></span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5 leading-snug">
            Emits regular card transactions. Baseline models perform with near-zero error.
          </p>
        </button>

        {/* Control 2: Introduce New Fraud Pattern */}
        <button
          onClick={() => {
            updateConfig({ fraud_regime: 'drift_evasion' });
            if (!isRunning) startSimulator();
          }}
          className={`flex flex-col p-3 rounded-lg border text-left transition-all cursor-pointer ${
            regime === 'drift_evasion'
              ? 'bg-cyan-950/50 border-cyan-400 shadow-lg shadow-cyan-950/50'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-cyan-300 uppercase tracking-wider">2. Introduce New Fraud Pattern</span>
            <span className={`w-2.5 h-2.5 rounded-full ${regime === 'drift_evasion' ? 'bg-cyan-400 animate-pulse' : 'bg-slate-700'}`}></span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5 leading-snug">
            Switches to nocturnal micro-velocity card testing. Fixed model recall crashes; concept drift is triggered.
          </p>
        </button>

        {/* Control 3: Enable Adaptive Learning */}
        <button
          onClick={() => updateConfig({ adaptive_learning_enabled: !adaptiveEnabled })}
          className={`flex flex-col p-3 rounded-lg border text-left transition-all cursor-pointer ${
            adaptiveEnabled
              ? 'bg-blue-950/40 border-blue-500/80 shadow-lg shadow-blue-950/50'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 opacity-70'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-300 uppercase tracking-wider">3. Adaptive Learning</span>
            <span className={`px-2 py-0.5 text-[10px] rounded font-mono font-bold ${
              adaptiveEnabled ? 'bg-blue-900 text-blue-200' : 'bg-slate-800 text-slate-400'
            }`}>
              {adaptiveEnabled ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5 leading-snug">
            Learns incrementally from verified feedback (`partial_fit`) to recover fraud capture rate.
          </p>
        </button>

      </div>

      {/* Sliders: Rate & Feedback Delay */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-3 border-t border-slate-800/80 text-xs">
        
        {/* Stream Speed Slider */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between font-mono">
            <span className="text-slate-400 flex items-center gap-1.5">
              <FastForward className="w-3.5 h-3.5 text-cyan-400" /> Transaction Rate:
            </span>
            <span className="text-cyan-300 font-bold">{intervalMs} ms ({Math.round(1000 / intervalMs)} tx/sec)</span>
          </div>
          <input
            type="range"
            min="100"
            max="2000"
            step="100"
            value={intervalMs}
            onChange={(e) => updateConfig({ interval_ms: parseInt(e.target.value) })}
            className="w-full accent-cyan-400 cursor-pointer"
          />
        </div>

        {/* Feedback Delay Slider */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between font-mono">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-blue-400" /> Verified Feedback Delay:
            </span>
            <span className="text-blue-300 font-bold">{(feedbackDelayMs / 1000).toFixed(1)}s</span>
          </div>
          <input
            type="range"
            min="500"
            max="10000"
            step="500"
            value={feedbackDelayMs}
            onChange={(e) => updateConfig({ feedback_delay_ms: parseInt(e.target.value) })}
            className="w-full accent-blue-400 cursor-pointer"
          />
        </div>

      </div>
    </div>
  );
}
