import React, { useState } from 'react';
import { History, RotateCcw } from 'lucide-react';

function ModelLifecycleComponent({ modelVersions, simulatorStatus, triggerRollback }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [rollbackMsg, setRollbackMsg] = useState('');
  const [isRollingBack, setIsRollingBack] = useState(false);

  const canRollback = simulatorStatus?.can_rollback ?? (modelVersions && modelVersions.length > 1);

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
    <div id="audit" className="bg-card border border-theme rounded-xl p-5 sm:p-6 theme-card-shadow">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3.5 border-b border-theme gap-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-accent-theme" />
          <h3 className="text-sm font-bold text-primary uppercase tracking-wider">
            Model Governance, Retraining Logs & Version Rollback
          </h3>
        </div>

        {/* Rollback Trigger Button */}
        <div>
          {!showConfirm ? (
            <div className="flex items-center gap-2">
              <button
                disabled={!canRollback}
                onClick={() => canRollback && setShowConfirm(true)}
                title={canRollback ? 'Restore previous stable model version' : 'Rollback disabled: No prior stable model version exists yet.'}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
                  canRollback
                    ? 'bg-card-subtle hover:bg-card-subtle/80 border-theme text-accent-theme cursor-pointer'
                    : 'bg-card-subtle/40 border-theme text-secondary opacity-50 cursor-not-allowed'
                }`}
              >
                <RotateCcw className="w-3.5 h-3.5" /> Rollback Version
              </button>
              {!canRollback && (
                <span className="text-[11px] font-mono text-secondary hidden md:inline">
                  (Initial v1.0 active)
                </span>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 bg-card-subtle border border-amber-500/50 p-1.5 rounded-lg">
              <span className="text-xs text-amber-500 font-medium">Confirm restore previous version?</span>
              <button
                onClick={handleRollback}
                disabled={isRollingBack}
                className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold cursor-pointer"
              >
                {isRollingBack ? 'Restoring...' : 'Confirm Rollback'}
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-2 py-1 rounded bg-card text-secondary hover:text-primary text-xs cursor-pointer border border-theme"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {rollbackMsg && (
        <div className="my-3 p-2.5 rounded bg-sky-500/10 border border-sky-500/30 text-xs sm:text-[13px] text-sky-600 dark:text-sky-300 font-mono">
          {rollbackMsg}
        </div>
      )}

      {/* Model Versions Audit Table */}
      <div className="overflow-x-auto mt-3.5">
        <table className="w-full text-left text-xs sm:text-[13px] font-mono border-collapse">
          <thead>
            <tr className="border-b border-theme text-secondary text-xs">
              <th className="py-2.5 px-3">Version Tag</th>
              <th className="py-2.5 px-3">Model Type</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Recall</th>
              <th className="py-2.5 px-3">F1-Score</th>
              <th className="py-2.5 px-3">Samples</th>
              <th className="py-2.5 px-3 text-right">Trained At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-subtle-theme">
            {modelVersions?.length === 0 ? (
              <tr>
                <td colSpan="7" className="py-8 text-center text-secondary italic">
                  <div className="max-w-md mx-auto text-center space-y-1">
                    <p className="font-semibold text-primary not-italic">No Retrained Versions Yet</p>
                    <p className="text-xs">Baseline adaptive model v1.0 is currently active. Candidate models will be listed here upon verified holdout evaluation.</p>
                  </div>
                </td>
              </tr>
            ) : (
              modelVersions.map((v) => {
                const isActive = v.status === 'active';
                const isCandidate = v.status === 'candidate';
                const isRolledBack = v.status === 'rolled_back';

                return (
                  <tr key={v.id} className={isActive ? 'bg-sky-500/5' : 'hover:bg-card-subtle/40'}>
                    <td className="py-2 px-3 font-bold text-primary flex items-center gap-1.5">
                      {isActive && <span className="w-1.5 h-1.5 rounded-full bg-accent-theme"></span>}
                      {v.version_tag}
                    </td>
                    <td className="py-2 px-3 text-secondary capitalize">{v.model_name}</td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isActive
                          ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                          : isCandidate
                          ? 'bg-blue-500/10 border border-blue-500/30 text-blue-600 dark:text-blue-400'
                          : isRolledBack
                          ? 'bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400'
                          : 'bg-card-subtle text-muted-custom'
                      }`}>
                        {v.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-primary font-bold">
                      {v.recall ? `${(v.recall * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td className="py-2 px-3 text-primary">
                      {v.f1_score ? v.f1_score.toFixed(3) : 'N/A'}
                    </td>
                    <td className="py-2 px-3 text-secondary">{v.sample_count?.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-muted-custom text-[10px]">
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

export default React.memo(ModelLifecycleComponent);
