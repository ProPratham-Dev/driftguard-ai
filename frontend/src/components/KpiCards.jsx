import React from 'react';
import { Layers, ShieldCheck, AlertTriangle, Cpu, Radio } from 'lucide-react';

function KpiCardsComponent({ simulatorStatus, driftStatus }) {
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

  const severityBadgeClass = {
    NORMAL: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400',
    WARNING: 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400 animate-pulse',
    CRITICAL: 'bg-rose-500/15 border-rose-500/40 text-rose-600 dark:text-rose-400 font-bold'
  };

  return (
    <div id="overview" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
      
      {/* 1. Transactions Processed */}
      <div className="bg-card border border-theme rounded-xl p-4 theme-card-shadow flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono text-secondary uppercase tracking-wider">Transactions</span>
          <div className="p-1.5 rounded-lg bg-card-subtle text-accent-theme">
            <Layers className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-primary">{totalTx.toLocaleString()}</div>
          <div className="text-[11px] text-secondary mt-1 flex items-center justify-between">
            <span>Verified:</span>
            <span className="font-mono text-accent-theme font-semibold">{feedbackCount.toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* 2. Fraud Detected */}
      <div className="bg-card border border-theme rounded-xl p-4 theme-card-shadow flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono text-secondary uppercase tracking-wider">Fraud Detected</span>
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500">
            <ShieldCheck className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-emerald-500 dark:text-emerald-400">{adaptiveDetected}</div>
          <div className="text-[11px] text-secondary mt-1 flex items-center justify-between">
            <span>Fixed Model caught:</span>
            <span className="font-mono text-primary font-medium">{fixedDetected} / {fraudSimulated}</span>
          </div>
        </div>
      </div>

      {/* 3. Fraud Missed (False Negatives) */}
      <div className="bg-card border border-theme rounded-xl p-4 theme-card-shadow flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono text-secondary uppercase tracking-wider">Missed Fraud (FN)</span>
          <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-500">
            <AlertTriangle className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-bold font-mono text-accent-theme">{adaptiveMissed}</span>
            <span className="text-[11px] text-secondary">adaptive</span>
          </div>
          <div className="text-[11px] text-secondary mt-1 flex items-center justify-between">
            <span>Fixed Missed:</span>
            <span className="font-mono font-bold text-rose-500">
              {fixedMissed} ({fraudSimulated > 0 ? `${Math.round((fixedMissed / fraudSimulated) * 100)}%` : '0%'})
            </span>
          </div>
        </div>
      </div>

      {/* 4. Active Model Version */}
      <div className="bg-card border border-theme rounded-xl p-4 theme-card-shadow flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono text-secondary uppercase tracking-wider">Adaptive Model</span>
          <div className="p-1.5 rounded-lg bg-card-subtle text-accent-theme">
            <Cpu className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-lg font-bold font-mono text-primary truncate" title={activeVersion}>
            {activeVersion}
          </div>
          <div className="text-[11px] text-secondary mt-1 flex items-center justify-between">
            <span>Fixed Baseline:</span>
            <span className="font-mono text-secondary">v1.0-static</span>
          </div>
        </div>
      </div>

      {/* 5. Concept Drift Severity */}
      <div className="bg-card border border-theme rounded-xl p-4 theme-card-shadow flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono text-secondary uppercase tracking-wider">Drift Severity</span>
          <div className="p-1.5 rounded-lg bg-card-subtle text-accent-theme">
            <Radio className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${severityBadgeClass[severity] || severityBadgeClass.NORMAL}`}>
              {severity}
            </span>
            <span className="text-xs font-mono text-secondary">Score: {Math.round(driftScore * 100)}%</span>
          </div>
          <div className="text-[11px] text-secondary mt-1 flex items-center justify-between">
            <span>Recent Error:</span>
            <span className="font-mono text-primary font-medium">
              {Math.round((driftStatus?.current_error_rate || 0) * 100)}%
            </span>
          </div>
        </div>
      </div>

    </div>
  );
}

export default React.memo(KpiCardsComponent);
