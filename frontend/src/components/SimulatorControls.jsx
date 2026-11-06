import React from 'react';
import { Play, Pause, Square, FastForward, Zap, Clock } from 'lucide-react';

function SimulatorControlsComponent({
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
    <div id="simulator" className="bg-card border border-theme rounded-xl p-5 sm:p-6 theme-card-shadow">
      
      {/* Title & Stream Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-theme gap-3">
        <div>
          <h2 className="text-sm font-bold text-primary flex items-center gap-2 tracking-wide uppercase">
            <Zap className="w-4 h-4 text-accent-theme" />
            Hackathon Demonstration Controls
          </h2>
          <p className="text-[13px] text-secondary mt-1">
            Interactive controls demonstrating concept drift emergence and online adaptive defense.
          </p>
        </div>

        {/* Engine State Buttons */}
        <div className="flex items-center gap-2">
          {!isRunning ? (
            <button
              onClick={startSimulator}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-white" /> Start Stream
            </button>
          ) : isPaused ? (
            <button
              onClick={resumeSimulator}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-white" /> Resume
            </button>
          ) : (
            <button
              onClick={pauseSimulator}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
            >
              <Pause className="w-3.5 h-3.5 fill-white" /> Pause
            </button>
          )}

          {isRunning && (
            <button
              onClick={stopSimulator}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-500 dark:text-rose-400 text-xs font-semibold transition-all cursor-pointer"
            >
              <Square className="w-3.5 h-3.5 fill-current" /> Stop
            </button>
          )}
        </div>
      </div>

      {/* 3 Core Hackathon Demo Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 my-4">
        
        {/* Step 1: Normal Traffic */}
        <button
          onClick={() => {
            updateConfig({ fraud_regime: 'normal' });
            if (!isRunning) startSimulator();
          }}
          className={`flex flex-col p-3.5 sm:p-4 rounded-xl border text-left transition-all cursor-pointer ${
            regime === 'normal'
              ? 'bg-emerald-500/10 border-emerald-500/50 shadow-xs'
              : 'bg-card-subtle/50 border-theme hover:border-emerald-500/30'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs sm:text-[13px] font-bold text-primary uppercase tracking-wider">
              1. Normal Traffic
            </span>
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                regime === 'normal' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400 dark:bg-slate-700'
              }`}
            />
          </div>
          <p className="text-xs sm:text-[13px] text-secondary mt-1.5 leading-relaxed">
            Emits benign card transactions. Both static and adaptive models operate with near-zero error.
          </p>
        </button>

        {/* Step 2: Introduce New Fraud Pattern */}
        <button
          onClick={() => {
            updateConfig({ fraud_regime: 'drift_evasion' });
            if (!isRunning) startSimulator();
          }}
          className={`flex flex-col p-3.5 sm:p-4 rounded-xl border text-left transition-all cursor-pointer ${
            regime === 'drift_evasion'
              ? 'bg-sky-500/10 border-sky-500/50 shadow-xs'
              : 'bg-card-subtle/50 border-theme hover:border-sky-500/30'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs sm:text-[13px] font-bold text-accent-theme uppercase tracking-wider">
              2. Introduce New Fraud Pattern
            </span>
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                regime === 'drift_evasion' ? 'bg-sky-400 animate-pulse' : 'bg-slate-400 dark:bg-slate-700'
              }`}
            />
          </div>
          <p className="text-xs sm:text-[13px] text-secondary mt-1.5 leading-relaxed">
            Switches to nocturnal micro-velocity evasion. Fixed model recall crashes; ASW-DD triggers CRITICAL drift.
          </p>
        </button>

        {/* Step 3: Enable Adaptive Learning */}
        <button
          onClick={() => updateConfig({ adaptive_learning_enabled: !adaptiveEnabled })}
          className={`flex flex-col p-3.5 sm:p-4 rounded-xl border text-left transition-all cursor-pointer ${
            adaptiveEnabled
              ? 'bg-blue-500/10 border-blue-500/50 shadow-xs'
              : 'bg-card-subtle/50 border-theme opacity-70'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs sm:text-[13px] font-bold text-primary uppercase tracking-wider">
              3. Adaptive Online Learning
            </span>
            <span
              className={`px-2 py-0.5 text-[10px] rounded font-mono font-bold ${
                adaptiveEnabled
                  ? 'bg-blue-500/20 text-accent-theme'
                  : 'bg-card-subtle text-muted-custom'
              }`}
            >
              {adaptiveEnabled ? 'ACTIVE' : 'OFF'}
            </span>
          </div>
          <p className="text-xs sm:text-[13px] text-secondary mt-1.5 leading-relaxed">
            Trains candidate models on delayed verified feedback and auto-promotes to restore fraud recall.
          </p>
        </button>

      </div>

      {/* Sliders: Rate & Feedback Delay */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-3.5 border-t border-theme text-xs sm:text-[13px]">
        
        {/* Stream Speed Slider */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between font-mono">
            <span className="text-secondary flex items-center gap-1.5">
              <FastForward className="w-3.5 h-3.5 text-accent-theme" /> Speed Interval:
            </span>
            <span className="text-primary font-bold">{intervalMs} ms ({Math.round(1000 / intervalMs)} tx/sec)</span>
          </div>
          <input
            type="range"
            min="100"
            max="2000"
            step="100"
            value={intervalMs}
            onChange={(e) => updateConfig({ interval_ms: parseInt(e.target.value) })}
            className="w-full accent-sky-500 cursor-pointer"
          />
        </div>

        {/* Feedback Delay Slider */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between font-mono">
            <span className="text-secondary flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-accent-theme" /> Feedback Arrival Delay:
            </span>
            <span className="text-primary font-bold">{(feedbackDelayMs / 1000).toFixed(1)}s</span>
          </div>
          <input
            type="range"
            min="500"
            max="10000"
            step="500"
            value={feedbackDelayMs}
            onChange={(e) => updateConfig({ feedback_delay_ms: parseInt(e.target.value) })}
            className="w-full accent-sky-500 cursor-pointer"
          />
        </div>

      </div>

    </div>
  );
}

export default React.memo(SimulatorControlsComponent);
