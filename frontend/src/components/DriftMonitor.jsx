import React, { useMemo } from 'react';
import { Radio, Clock } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { useTheme } from '../context/ThemeContext';

function DriftMonitorComponent({ driftStatus, driftEvents }) {
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

  // Build timeline chart data from recent drift events or recent observations
  const timelineData = useMemo(() => {
    if (!driftEvents || driftEvents.length === 0) {
      return [
        { time: 'T-4', error: refError * 100 },
        { time: 'T-3', error: refError * 100 },
        { time: 'T-2', error: refError * 100 },
        { time: 'T-1', error: refError * 100 },
        { time: 'Now', error: recentError * 100 }
      ];
    }
    return driftEvents.slice(0, 8).reverse().map((evt, idx) => ({
      time: `E${idx + 1}`,
      error: Math.round((evt.post_drift_mean || 0) * 100)
    }));
  }, [driftEvents, recentError, refError]);

  const gridColor = isDark ? '#1e293b' : '#E2E8F0';
  const textColor = isDark ? '#94A3B8' : '#64748B';
  const tooltipBg = isDark ? '#151F30' : '#FFFFFF';
  const tooltipBorder = isDark ? '#263449' : '#E5EAF2';

  return (
    <div id="drift" className="bg-card border border-theme rounded-xl p-5 sm:p-6 theme-card-shadow flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-theme">
          <div className="flex items-center gap-2">
            <Radio className={`w-4 h-4 ${severity === 'CRITICAL' ? 'text-rose-500 animate-pulse' : 'text-accent-theme'}`} />
            <h3 className="text-sm font-bold text-primary uppercase tracking-wider">
              Concept Drift Detector (ASW-DD)
            </h3>
          </div>
          <span className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-bold border ${severityBadgeClass[severity] || severityBadgeClass.NORMAL}`}>
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

        {/* Trend Area Chart */}
        <div className="h-28 w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timelineData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
              <XAxis dataKey="time" stroke={textColor} fontSize={11} tickLine={false} />
              <YAxis stroke={textColor} fontSize={11} domain={[0, 50]} unit="%" tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: tooltipBg,
                  borderColor: tooltipBorder,
                  borderRadius: '6px',
                  fontSize: '12px',
                  color: isDark ? '#F1F5F9' : '#172033'
                }}
                formatter={(val) => [`${val}%`, 'Error Rate']}
              />
              <Area
                type="monotone"
                dataKey="error"
                stroke={isDark ? '#38BDF8' : '#2563EB'}
                fill={isDark ? '#38BDF822' : '#2563EB22'}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Drift Events Timeline Log */}
      <div className="mt-3.5 pt-3.5 border-t border-theme">
        <span className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1.5 mb-2">
          <Clock className="w-3.5 h-3.5 text-accent-theme" /> Event Log
        </span>

        {driftEvents?.length === 0 ? (
          <div className="p-3 rounded-lg bg-card-subtle/50 border border-theme text-xs text-secondary italic flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            No drift events detected yet. Click "2. Introduce New Fraud Pattern" above to initiate evasion traffic.
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
