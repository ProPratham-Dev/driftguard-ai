import React from 'react';
import { Layers, ShieldCheck, AlertTriangle, Cpu, Radio } from 'lucide-react';

export default function KpiCards({ simulatorStatus, driftStatus }) {
  const totalTx = simulatorStatus?.transactions_generated || 0;
  const feedbackCount = simulatorStatus?.feedback_processed || 0;
  const fraudSimulated = simulatorStatus?.fraud_count_simulated || 0;
  const adaptiveDetected = simulatorStatus?.fraud_detected_adaptive || 0;
  const fixedDetected = simulatorStatus?.fraud_detected_fixed || 0;
  const adaptiveMissed = simulatorStatus?.fraud_missed_adaptive || 0;
  const fixedMissed = simulatorStatus?.fraud_missed_fixed || 0;

  const severity = driftStatus?.severity || 'NORMAL';
  const driftScore = driftStatus?.drift_score || 0.0;
  const activeVersion = simulatorStatus?.active_adaptive_version || 'v1.0-baseline';

  const severityStyles = {
    NORMAL: 'bg-emerald-950/40 border-emerald-800/60 text-emerald-400',
    WARNING: 'bg-amber-950/40 border-amber-800/60 text-amber-400 animate-pulse',
    CRITICAL: 'bg-rose-950/50 border-rose-700 text-rose-300 animate-bounce'
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      
      {/* 1. Transactions Processed */}
      <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Transactions</span>
          <div className="p-2 rounded-lg bg-blue-950/60 border border-blue-800/50 text-blue-400">
            <Layers className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-white">{totalTx.toLocaleString()}</div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Verified:</span>
            <span className="font-mono text-cyan-400">{feedbackCount.toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* 2. Fraud Detected */}
      <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Fraud Detected</span>
          <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/50 text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-emerald-400">{adaptiveDetected}</div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Fixed Model caught:</span>
            <span className="font-mono text-slate-300">{fixedDetected} / {fraudSimulated}</span>
          </div>
        </div>
      </div>

      {/* 3. Fraud Missed (False Negatives) */}
      <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Undetected Fraud (FN)</span>
          <div className="p-2 rounded-lg bg-rose-950/60 border border-rose-800/50 text-rose-400">
            <AlertTriangle className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-cyan-400">{adaptiveMissed}</span>
            <span className="text-xs text-slate-400">adaptive</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Fixed Missed:</span>
            <span className="font-mono font-bold text-rose-400">{fixedMissed} ({fraudSimulated > 0 ? `${Math.round((fixedMissed/fraudSimulated)*100)}%` : '0%'})</span>
          </div>
        </div>
      </div>

      {/* 4. Active Model Version */}
      <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Adaptive Model</span>
          <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
            <Cpu className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-lg font-bold font-mono text-cyan-300 truncate" title={activeVersion}>
            {activeVersion}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Fixed Baseline:</span>
            <span className="font-mono text-slate-400">v1.0-static</span>
          </div>
        </div>
      </div>

      {/* 5. Concept Drift Severity */}
      <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Drift Severity</span>
          <div className="p-2 rounded-lg bg-purple-950/60 border border-purple-800/50 text-purple-400">
            <Radio className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold border ${severityStyles[severity] || severityStyles.NORMAL}`}>
              {severity}
            </span>
            <span className="text-xs font-mono text-slate-400">Score: {Math.round(driftScore * 100)}%</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Recent Error:</span>
            <span className="font-mono text-slate-300">{Math.round((driftStatus?.current_error_rate || 0) * 100)}%</span>
          </div>
        </div>
      </div>

    </div>
  );
}
