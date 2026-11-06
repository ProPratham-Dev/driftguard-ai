import React from 'react';
import { Layers, ShieldCheck, ShieldAlert, Clock, ArrowUpRight } from 'lucide-react';

export default function LiveTransactionFeed({ transactions }) {
  return (
    <div className="bg-[#0b1428] border border-slate-800/80 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Live Transaction Stream & Pre-Feedback Predictions
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          Showing latest {transactions?.length || 0} transactions
        </span>
      </div>

      <div className="overflow-x-auto mt-3">
        <table className="w-full text-left text-xs font-mono border-collapse">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
              <th className="py-2.5 px-3">TX ID</th>
              <th className="py-2.5 px-3">Amount</th>
              <th className="py-2.5 px-3">Category</th>
              <th className="py-2.5 px-3">Velocity / Device</th>
              <th className="py-2.5 px-3">Fixed Model</th>
              <th className="py-2.5 px-3">Adaptive Model</th>
              <th className="py-2.5 px-3">Delayed Feedback</th>
              <th className="py-2.5 px-3 text-right">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {transactions?.length === 0 ? (
              <tr>
                <td colSpan="8" className="py-8 text-center text-slate-500 italic">
                  No live transactions received yet. Click "Start Stream" or "1. Start Normal Traffic" above.
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
                    className={`transition-colors duration-200 ${
                      isDiscrepancy
                        ? 'bg-cyan-950/20 hover:bg-cyan-950/30'
                        : isAdaptiveFraud
                        ? 'bg-rose-950/15 hover:bg-rose-950/25'
                        : 'hover:bg-slate-900/50'
                    }`}
                  >
                    {/* TX ID */}
                    <td className="py-2 px-3 font-semibold text-white truncate max-w-[130px]">
                      {tx.tx_id}
                    </td>

                    {/* Amount */}
                    <td className="py-2 px-3 font-bold text-slate-200">
                      ${tx.amount?.toFixed(2)}
                    </td>

                    {/* Category */}
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-900 text-slate-300 border border-slate-800">
                        {tx.merchant_category}
                      </span>
                    </td>

                    {/* Velocity / Device */}
                    <td className="py-2 px-3 text-[11px] text-slate-400">
                      <span className={tx.velocity_1h >= 6 ? 'text-amber-400 font-bold' : ''}>
                        {tx.velocity_1h}/hr
                      </span>{' '}
                      | Trust: {(tx.device_trust_score * 100).toFixed(0)}%
                    </td>

                    {/* Fixed Model */}
                    <td className="py-2 px-3">
                      {isFixedFraud ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-rose-950 border border-rose-800 text-rose-300 font-bold">
                          FRAUD ({(tx.fixed_score * 100).toFixed(0)}%)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-900 border border-slate-800 text-slate-400">
                          LEGIT ({(tx.fixed_score * 100).toFixed(0)}%)
                        </span>
                      )}
                    </td>

                    {/* Adaptive Model */}
                    <td className="py-2 px-3">
                      {isAdaptiveFraud ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-950 border border-cyan-500 text-cyan-300 font-bold shadow-sm shadow-cyan-500/20">
                          FRAUD ({(tx.adaptive_score * 100).toFixed(0)}%)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-900 border border-slate-800 text-slate-400">
                          LEGIT ({(tx.adaptive_score * 100).toFixed(0)}%)
                        </span>
                      )}
                    </td>

                    {/* Delayed Feedback */}
                    <td className="py-2 px-3">
                      {!isVerified ? (
                        <span className="flex items-center gap-1 text-[10px] text-amber-400">
                          <Clock className="w-3 h-3 animate-spin" /> Pending verification...
                        </span>
                      ) : isTrueFraud ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-rose-900/60 border border-rose-600 text-rose-200 font-bold">
                          VERIFIED FRAUD
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 border border-emerald-800 text-emerald-300">
                          VERIFIED LEGIT
                        </span>
                      )}
                    </td>

                    {/* Time */}
                    <td className="py-2 px-3 text-right text-slate-500 text-[10px]">
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
