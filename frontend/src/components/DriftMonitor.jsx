import React, { useMemo } from 'react';
import { Radio, Clock, AlertTriangle, ShieldCheck, Info } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer
} from 'recharts';
import { useTheme } from '../context/ThemeContext';

function DriftMonitorComponent({ driftStatus, driftEvents, driftHistory = [] }) {
  const { isDark } = useTheme();

  const severity = driftStatus?.severity || 'NORMAL';
  const driftScore = driftStatus?.drift_score || 0.0;
  const recentError = driftStatus?.current_error_rate || 0.0;
  const refError = driftStatus?.reference_error_rate || 0.0;
  const recentCount = driftStatus?.recent_samples_count || 0;
  const message = driftStatus?.status_message || 'Monitoring transaction stream...';

  const severityBadgeClass = {
    NORMAL: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400',
    WARNING: 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400 animate-pulse',
    CRITICAL: 'bg-rose-500/15 border-rose-500/40 text-rose-600 dark:text-rose-400 font-bold'
  };

  // Build dual-model rolling error time-series from verified feedback history
  const chartData = useMemo(() => {
    if (!driftHistory || driftHistory.length === 0) {
      return [];
    }

    return driftHistory.map((item, index) => {
      let timeLabel = `#${index + 1}`;
      if (item.timestamp) {
        try {
          const d = new Date(item.timestamp);
          timeLabel = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch {
          timeLabel = `#${index + 1}`;
        }
      }

      const adaptErr = item.adaptive_rolling_error !== undefined
        ? Math.round(item.adaptive_rolling_error * 1000) / 10
        : (item.adaptive_error ? 100 : 0);

      const fixedErr = item.fixed_rolling_error !== undefined
        ? Math.round(item.fixed_rolling_error * 1000) / 10
        : (item.fixed_error ? 100 : 0);

      const refErr = item.reference_error_rate !== undefined
        ? Math.round(item.reference_error_rate * 1000) / 10
        : Math.round(refError * 1000) / 10;

      return {
        tx_id: item.tx_id,
        time: timeLabel,
        fullTime: item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : timeLabel,
        adaptive: adaptErr,
        fixed: fixedErr,
        ref: refErr,
        adaptiveErrorRaw: item.adaptive_error,
        fixedErrorRaw: item.fixed_error,
        groundTruth: item.ground_truth,
        adaptivePred: item.adaptive_prediction,
        fixedPred: item.fixed_prediction
      };
    });
  }, [driftHistory, refError]);

  const hasData = chartData.length > 0;
  const maxError = hasData ? Math.max(...chartData.map((d) => Math.max(d.adaptive, d.fixed, d.ref))) : 0;
  const isAllZero = hasData && maxError === 0;
  const isWarmup = hasData && chartData.length < 15;

  // Sensible dynamic Y-axis domain
  const yDomain = useMemo(() => {
    if (!hasData || maxError <= 5) {
      return [0, 15]; // clean breathing room so 0% values remain visually distinguishable
    }
    if (maxError <= 25) {
      return [0, 30];
    }
    return [0, Math.min(100, Math.ceil((maxError + 5) / 10) * 10)];
  }, [hasData, maxError]);

  const gridColor = isDark ? '#1e293b' : '#E2E8F0';
  const textColor = isDark ? '#94A3B8' : '#64748B';
  const tooltipBg = isDark ? '#151F30' : '#FFFFFF';
  const tooltipBorder = isDark ? '#263449' : '#E5EAF2';

  // Custom high-fidelity tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const pt = payload[0].payload;
    return (
      <div
        className="p-3 rounded-lg border shadow-lg text-xs font-mono space-y-1.5"
        style={{
          backgroundColor: tooltipBg,
          borderColor: tooltipBorder,
          color: isDark ? '#F1F5F9' : '#172033'
        }}
      >
        <div className="font-bold border-b pb-1 flex justify-between gap-4 border-slate-700/30 text-secondary">
          <span>TX: {pt.tx_id}</span>
          <span>{pt.fullTime}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 font-semibold text-sky-400">
            <span className="w-2 h-2 rounded-full bg-sky-400"></span> Adaptive Error:
          </span>
          <span className="font-bold">{pt.adaptive.toFixed(1)}%</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 font-semibold text-rose-500">
            <span className="w-2 h-2 rounded-full bg-rose-500"></span> Fixed Error:
          </span>
          <span className="font-bold">{pt.fixed.toFixed(1)}%</span>
        </div>
        <div className="flex items-center justify-between gap-4 text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-0.5 bg-slate-400"></span> Ref Baseline:
          </span>
          <span>{pt.ref.toFixed(1)}%</span>
        </div>
        <div className="pt-1 text-[11px] text-secondary border-t border-slate-700/20 flex justify-between">
          <span>Ground Truth: {pt.groundTruth === 1 ? 'FRAUD' : 'LEGIT'}</span>
          <span>Adaptive: {pt.adaptivePred === 1 ? 'FRAUD' : 'LEGIT'}</span>
        </div>
      </div>
    );
  };

  return (
    <div id="drift" className="bg-card border border-theme rounded-xl p-5 sm:p-6 theme-card-shadow flex flex-col justify-between">
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-theme gap-2">
          <div className="flex items-center gap-2">
            <Radio className={`w-4 h-4 ${severity === 'CRITICAL' ? 'text-rose-500 animate-pulse' : 'text-accent-theme'}`} />
            <div>
              <h3 className="text-sm font-bold text-primary uppercase tracking-wider">
                Concept Drift Detector (ASW-DD)
              </h3>
              <p className="text-[11px] text-secondary font-mono">
                Sliding-window monitor calibrated on N=4,800 concept-drift benchmark
              </p>
            </div>
          </div>
          <span className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-bold border self-start sm:self-auto ${severityBadgeClass[severity] || severityBadgeClass.NORMAL}`}>
            {severity}
          </span>
        </div>

        {/* Live Sub-Window Gauges */}
        <div className="grid grid-cols-2 gap-3.5 my-3.5">
          <div className="bg-card-subtle border border-theme rounded-lg p-3.5">
            <span className="text-xs uppercase font-mono font-semibold text-secondary">Recent Window Error</span>
            <div className="text-2xl font-bold font-mono text-primary mt-1">
              {(recentError * 100).toFixed(1)}%
            </div>
            <span className="text-[11px] text-secondary font-mono">Last {recentCount} verified</span>
          </div>

          <div className="bg-card-subtle border border-theme rounded-lg p-3.5">
            <span className="text-xs uppercase font-mono font-semibold text-secondary">Reference Window Error</span>
            <div className="text-2xl font-bold font-mono text-primary mt-1">
              {(refError * 100).toFixed(1)}%
            </div>
            <span className="text-[11px] text-secondary font-mono">Historical baseline</span>
          </div>
        </div>

        {/* Drift Score Meter */}
        <div className="space-y-1.5 my-2.5">
          <div className="flex justify-between text-xs sm:text-[13px] font-mono">
            <span className="text-secondary font-medium">Normalized Drift Score:</span>
            <span className={`font-bold ${driftScore > 0.6 ? 'text-rose-500' : driftScore > 0.3 ? 'text-amber-500' : 'text-emerald-500'}`}>
              {(driftScore * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full h-2.5 bg-card-subtle rounded-full overflow-hidden border border-theme">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                driftScore > 0.6 ? 'bg-rose-500' : driftScore > 0.3 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(3, driftScore * 100))}%` }}
            />
          </div>
        </div>

        {/* Informational Status Callouts */}
        {hasData && isAllZero && (
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs font-mono text-emerald-600 dark:text-emerald-400 my-2">
            <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-500" />
            <span>Zero Misclassifications: 0.0% rolling error across last {chartData.length} verified samples (both models 100% accurate).</span>
          </div>
        )}

        {hasData && isWarmup && !isAllZero && (
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/30 text-xs font-mono text-sky-600 dark:text-sky-400 my-2">
            <Info className="w-4 h-4 shrink-0 text-accent-theme" />
            <span>Warm-up Stream: {chartData.length}/15 verified samples collected. Rolling error window stabilizing.</span>
          </div>
        )}

        {/* Dual-Model Prediction Error Time-Series Chart */}
        {!hasData ? (
          <div className="h-44 w-full flex flex-col items-center justify-center p-4 rounded-lg bg-card-subtle/40 border border-theme text-center my-2">
            <Radio className="w-6 h-6 text-accent-theme/60 animate-pulse mb-2" />
            <p className="text-xs font-semibold text-primary">No Verified Feedback Samples Yet</p>
            <p className="text-[11px] text-secondary mt-1 max-w-sm">
              Rolling error trajectories plot in real time as transactions complete delayed verification. Click "Start Stream" above to stream transactions.
            </p>
          </div>
        ) : (
          <div className="h-44 w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 8, right: 12, left: -22, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis
                  dataKey="time"
                  stroke={textColor}
                  fontSize={10}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  stroke={textColor}
                  fontSize={10}
                  domain={yDomain}
                  unit="%"
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }}
                  iconType="circle"
                  iconSize={7}
                />
                {/* 0% Baseline Reference Line */}
                <ReferenceLine y={0} stroke={gridColor} strokeWidth={1} />
                {/* Detector Reference Baseline */}
                <Line
                  type="monotone"
                  name="ASW-DD Ref Baseline"
                  dataKey="ref"
                  stroke={isDark ? '#64748B' : '#94A3B8'}
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                {/* Fixed Model Rolling Error Series */}
                <Line
                  type="monotone"
                  name="Fixed Model Error"
                  dataKey="fixed"
                  stroke={isDark ? '#F43F5E' : '#E11D48'}
                  strokeWidth={2}
                  dot={{ r: 2.5, fill: isDark ? '#F43F5E' : '#E11D48', strokeWidth: 0 }}
                  activeDot={{ r: 4.5 }}
                  isAnimationActive={false}
                />
                {/* Adaptive Model Rolling Error Series */}
                <Line
                  type="monotone"
                  name="Adaptive Model Error (ASW-DD Input)"
                  dataKey="adaptive"
                  stroke={isDark ? '#38BDF8' : '#2563EB'}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: isDark ? '#38BDF8' : '#2563EB', strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Drift Events Timeline Log */}
      <div className="mt-3.5 pt-3.5 border-t border-theme">
        <span className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1.5 mb-2">
          <Clock className="w-3.5 h-3.5 text-accent-theme" /> Event Log
        </span>

        {driftEvents?.length === 0 ? (
          <div className="p-3 rounded-lg bg-card-subtle/50 border border-theme text-xs text-secondary italic flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            No drift threshold events detected yet. Click "2. Introduce New Fraud Pattern" above to trigger evasion drift.
          </div>
        ) : (
          <div className="space-y-1.5 max-h-24 overflow-y-auto pr-1">
            {driftEvents.slice(0, 3).map((evt, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs font-mono p-2 rounded bg-card-subtle border border-theme">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  evt.severity === 'CRITICAL'
                    ? 'bg-rose-500/20 text-rose-500'
                    : 'bg-amber-500/20 text-amber-500'
                }`}>
                  {evt.severity}
                </span>
                <span className="text-primary truncate max-w-[200px]">{evt.details || 'Error rate shift'}</span>
                <span className="text-secondary text-[11px]">{new Date(evt.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default React.memo(DriftMonitorComponent);
