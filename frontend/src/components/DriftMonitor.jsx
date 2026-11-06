import React from 'react';
import { Radio, AlertOctagon, Activity, Clock, ShieldAlert } from 'lucide-react';

export default function DriftMonitor({ driftStatus, driftEvents }) {
  const severity = driftStatus?.severity || 'NORMAL';
  const driftScore = driftStatus?.drift_score || 0.0;
  const recentError = driftStatus?.current_error_rate || 0.0;
  const refError = driftStatus?.reference_error_rate || 0.0;
  const recentCount = driftStatus?.recent_samples_count || 0;
  const message = driftStatus?.status_message || 'Monitoring transaction stream...';

  const severityBadge = {
    NORMAL: 'bg-emerald-950/60 border-emerald-600 text-emerald-400',
    WARNING: 'bg-amber-950/60 border-amber-600 text-amber-300 animate-pulse',
    CRITICAL: 'bg-rose-950/70 border-rose-600 text-rose-200 animate-bounce'
  };

  return (
    <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-5 shadow-xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Radio className={`w-5 h-5 ${severity === 'CRITICAL' ? 'text-rose-400 animate-pulse' : 'text-cyan-400'}`} />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Concept Drift Detector (ASW-DD)
            </h3>
          </div>
          <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold border ${severityBadge[severity] || severityBadge.NORMAL}`}>
            {severity}
          </span>
        </div>

        {/* Live Gauges */}
        <div className="grid grid-cols-2 gap-3 my-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] uppercase font-mono text-slate-400">Recent Window Error</span>
            <div className="text-xl font-bold font-mono text-white mt-1">
              {(recentError * 100).toFixed(1)}%
            </div>
            <span className="text-[10px] text-slate-500 font-mono">Last {recentCount} verified</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
            <span className="text-[10px] uppercase font-mono text-slate-400">Reference Window Error</span>
            <div className="text-xl font-bold font-mono text-slate-300 mt-1">
              {(refError * 100).toFixed(1)}%
            </div>
            <span className="text-[10px] text-slate-500 font-mono">Historical baseline</span>
          </div>
        </div>

        {/* Drift Score Meter */}
        <div className="space-y-1.5 my-3">
          <div className="flex justify-between text-xs font-mono">
            <span className="text-slate-400">Normalized Drift Score:</span>
            <span className={`font-bold ${driftScore > 0.6 ? 'text-rose-400' : driftScore > 0.3 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {(driftScore * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden p-0.5 border border-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                driftScore > 0.6 ? 'bg-rose-500 shadow-sm shadow-rose-500/50' : driftScore > 0.3 ? 'bg-amber-400' : 'bg-emerald-400'
              }`}
              style={{ width: `${Math.min(100, Math.max(4, driftScore * 100))}%` }}
            />
          </div>
        </div>

        {/* Status Message */}
        <div className="text-[11px] p-2.5 rounded bg-slate-900/60 border border-slate-800 text-slate-300 font-mono mt-3">
          {message}
        </div>
      </div>

      {/* Drift Events Timeline */}
      <div className="mt-4 pt-3 border-t border-slate-800/80">
        <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5 mb-2">
          <Clock className="w-3.5 h-3.5 text-cyan-400" /> Recent Drift Detections
        </span>

        {driftEvents?.length === 0 ? (
          <div className="text-[11px] text-slate-500 italic py-2">
            No drift events detected yet. Click "Introduce New Fraud Pattern" to simulate evasion.
          </div>
        ) : (
          <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
            {driftEvents.slice(0, 4).map((evt, idx) => (
              <div key={idx} className="flex items-center justify-between text-[11px] font-mono p-1.5 rounded bg-slate-900 border border-slate-800">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  evt.severity === 'CRITICAL' ? 'bg-rose-950 text-rose-300' : 'bg-amber-950 text-amber-300'
                }`}>
                  {evt.severity}
                </span>
                <span className="text-slate-300 truncate max-w-[180px]">{evt.details || 'Error rate shift'}</span>
                <span className="text-slate-500 text-[10px]">{new Date(evt.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
