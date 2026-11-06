import React, { useState } from 'react';
import { History, RotateCcw, Check, AlertCircle, Shield } from 'lucide-react';

export default function ModelLifecycle({ modelVersions, triggerRollback }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [rollbackMsg, setRollbackMsg] = useState('');
  const [isRollingBack, setIsRollingBack] = useState(false);

  const handleRollback = async () => {
    setIsRollingBack(true);
    try {
      const res = await triggerRollback();
      setRollbackMsg(res.message);
      setShowConfirm(false);
    } catch (err) {
      setRollbackMsg('Failed to rollback model.');
    } finally {
      setIsRollingBack(false);
    }
  };

  return (
    <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-5 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800 gap-3">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Model Version Governance & Rollback History
          </h3>
        </div>

        {/* Rollback Trigger Button */}
        <div>
          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-cyan-300 transition-all cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Rollback Adaptive Version
            </button>
          ) : (
            <div className="flex items-center gap-2 bg-slate-900 border border-amber-600/60 p-1.5 rounded-lg">
              <span className="text-[11px] text-amber-300">Confirm restore previous version?</span>
              <button
                onClick={handleRollback}
                disabled={isRollingBack}
                className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold cursor-pointer"
              >
                {isRollingBack ? 'Restoring...' : 'Yes, Rollback'}
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-2 py-1 rounded bg-slate-800 text-slate-300 text-xs cursor-pointer"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {rollbackMsg && (
        <div className="my-3 p-2.5 rounded bg-cyan-950/40 border border-cyan-800 text-xs text-cyan-300 font-mono">
          {rollbackMsg}
        </div>
      )}

      {/* Model Versions Table */}
      <div className="overflow-x-auto mt-3">
        <table className="w-full text-left text-xs font-mono border-collapse">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
              <th className="py-2 px-3">Version Tag</th>
              <th className="py-2 px-3">Model Type</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3">Recall</th>
              <th className="py-2 px-3">F1-Score</th>
              <th className="py-2 px-3">Samples</th>
              <th className="py-2 px-3 text-right">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {modelVersions?.length === 0 ? (
              <tr>
                <td colSpan="7" className="py-6 text-center text-slate-500 italic">
                  No version history records found.
                </td>
              </tr>
            ) : (
              modelVersions.map((v) => {
                const isActive = v.status === 'active';
                const isCandidate = v.status === 'candidate';
                const isRolledBack = v.status === 'rolled_back';

                return (
                  <tr key={v.id} className={isActive ? 'bg-cyan-950/15' : 'hover:bg-slate-900/40'}>
                    <td className="py-2 px-3 font-bold text-white flex items-center gap-1.5">
                      {isActive && <span className="w-2 h-2 rounded-full bg-cyan-400"></span>}
                      {v.version_tag}
                    </td>
                    <td className="py-2 px-3 text-slate-300 capitalize">{v.model_name}</td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isActive
                          ? 'bg-emerald-950 border border-emerald-700 text-emerald-300'
                          : isCandidate
                          ? 'bg-blue-950 border border-blue-700 text-blue-300'
                          : isRolledBack
                          ? 'bg-amber-950 border border-amber-700 text-amber-300'
                          : 'bg-slate-900 text-slate-500'
                      }`}>
                        {v.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-200 font-bold">
                      {v.recall ? `${(v.recall * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td className="py-2 px-3 text-slate-200">
                      {v.f1_score ? v.f1_score.toFixed(3) : 'N/A'}
                    </td>
                    <td className="py-2 px-3 text-slate-400">{v.sample_count?.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-slate-500 text-[10px]">
                      {v.trained_at ? new Date(v.trained_at).toLocaleString() : 'initial'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
