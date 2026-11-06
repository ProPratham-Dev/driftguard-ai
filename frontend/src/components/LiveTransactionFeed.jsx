import React from 'react';
import { Layers, Clock, ShieldCheck, AlertCircle } from 'lucide-react';

function LiveTransactionFeedComponent({ transactions }) {
  return (
    <div id="transactions" className="bg-card border border-theme rounded-xl p-5 theme-card-shadow">
      <div className="flex items-center justify-between pb-3 border-b border-theme">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-accent-theme" />
          <h3 className="text-xs font-bold text-primary uppercase tracking-wider">
            Live Streaming Transactions & Real-Time Predictions
          </h3>
        </div>
        <span className="text-[11px] font-mono text-secondary">
          Buffered latest {transactions?.length || 0} / 100 records
        </span>
      </div>

      <div className="overflow-x-auto mt-3">
        <table className="w-full text-left text-xs font-mono border-collapse">
          <thead>
            <tr className="border-b border-theme text-secondary text-[11px]">
              <th className="py-2.5 px-3">TX ID</th>
              <th className="py-2.5 px-3">Amount</th>
              <th className="py-2.5 px-3">Category</th>
              <th className="py-2.5 px-3">Velocity / Trust</th>
              <th className="py-2.5 px-3">Fixed Model</th>
              <th className="py-2.5 px-3">Adaptive Model</th>
              <th className="py-2.5 px-3">Delayed Feedback</th>
              <th className="py-2.5 px-3 text-right">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-subtle-theme">
            {transactions?.length === 0 ? (
              <tr>
                <td colSpan="8" className="py-8 text-center text-secondary italic">
                  No live transactions received yet. Click "Start Stream" or "1. Normal Traffic" above.
                </td>
              </tr>
            ) : (
              transactions.map((tx) => {
                const isFixedFraud = tx.fixed_prediction === 1;
                const isAdaptiveFraud = tx.adaptive_prediction === 1;
                const isDiscrepancy = isFixedFraud !== isAdaptiveFraud;
                const isVerified = tx.feedback_status === 'verified';
                const isTrueFraud = isVerified && tx.ground_truth === 1;

                return (
                  <tr
                    key={tx.tx_id}
                    className={`transition-colors duration-150 ${
                      isDiscrepancy
                        ? 'bg-sky-500/5 hover:bg-sky-500/10'
                        : isAdaptiveFraud
                        ? 'bg-rose-500/5 hover:bg-rose-500/10'
                        : 'hover:bg-card-subtle/50'
                    }`}
                  >
                    {/* TX ID */}
                    <td className="py-2 px-3 font-semibold text-primary truncate max-w-[130px]">
                      {tx.tx_id}
                    </td>

                    {/* Amount */}
                    <td className="py-2 px-3 font-bold text-primary">
                      ${tx.amount?.toFixed(2)}
                    </td>

                    {/* Category */}
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-card-subtle text-secondary border border-theme">
                        {tx.merchant_category}
                      </span>
                    </td>

                    {/* Velocity / Trust */}
                    <td className="py-2 px-3 text-[11px] text-secondary">
                      <span className={tx.velocity_1h >= 6 ? 'text-amber-500 font-bold' : ''}>
                        {tx.velocity_1h}/hr
                      </span>{' '}
                      | Trust: {(tx.device_trust_score * 100).toFixed(0)}%
                    </td>

                    {/* Fixed Model Output */}
                    <td className="py-2 px-3">
                      {isFixedFraud ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/15 border border-rose-500/40 text-rose-600 dark:text-rose-400 font-bold">
                          FRAUD ({(tx.fixed_score * 100).toFixed(0)}%)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-card-subtle border border-theme text-secondary">
                          LEGIT ({(tx.fixed_score * 100).toFixed(0)}%)
                        </span>
                      )}
                    </td>

                    {/* Adaptive Model Output */}
                    <td className="py-2 px-3">
                      {isAdaptiveFraud ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-sky-500/15 border border-sky-500/40 text-sky-600 dark:text-sky-300 font-bold">
                          FRAUD ({(tx.adaptive_score * 100).toFixed(0)}%)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-card-subtle border border-theme text-secondary">
                          LEGIT ({(tx.adaptive_score * 100).toFixed(0)}%)
                        </span>
                      )}
                    </td>

                    {/* Delayed Verified Feedback */}
                    <td className="py-2 px-3">
                      {!isVerified ? (
                        <span className="flex items-center gap-1 text-[10px] text-amber-500">
                          <Clock className="w-3 h-3 animate-spin" /> Pending verification...
                        </span>
                      ) : isTrueFraud ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 border border-rose-500/40 text-rose-600 dark:text-rose-300 font-bold">
                          VERIFIED FRAUD
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                          VERIFIED LEGIT
                        </span>
                      )}
                    </td>

                    {/* Time */}
                    <td className="py-2 px-3 text-right text-muted-custom text-[10px]">
                      {tx.timestamp ? new Date(tx.timestamp).toLocaleTimeString() : 'now'}
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

export default React.memo(LiveTransactionFeedComponent);
