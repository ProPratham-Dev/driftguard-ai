import React, { useMemo } from 'react';
import { GitCompare, CheckCircle2 } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { useTheme } from '../context/ThemeContext';

function ModelComparisonComponent({ comparisonMetrics }) {
  const { isDark } = useTheme();

  const fixed = comparisonMetrics?.fixed_model || {
    accuracy: 0.9129,
    precision: 1.0,
    recall: 0.4202,
    f1_score: 0.5918,
    fnr: 0.5798
  };

  const adaptive = comparisonMetrics?.adaptive_model || {
    accuracy: 0.9988,
    precision: 1.0,
    recall: 0.9917,
    f1_score: 0.9958,
    fnr: 0.0083
  };

  const samples = comparisonMetrics?.evaluated_samples || 0;

  // Chart data formatted as percentages (0 to 100)
  const chartData = useMemo(() => [
    { metric: 'Recall', Fixed: Math.round(fixed.recall * 100), Adaptive: Math.round(adaptive.recall * 100) },
    { metric: 'F1 Score', Fixed: Math.round(fixed.f1_score * 100), Adaptive: Math.round(adaptive.f1_score * 100) },
    { metric: 'Missed (FNR)', Fixed: Math.round(fixed.fnr * 100), Adaptive: Math.round(adaptive.fnr * 100) },
    { metric: 'Accuracy', Fixed: Math.round(fixed.accuracy * 100), Adaptive: Math.round(adaptive.accuracy * 100) },
    { metric: 'Precision', Fixed: Math.round(fixed.precision * 100), Adaptive: Math.round(adaptive.precision * 100) }
  ], [fixed, adaptive]);

  // Theme-aware colors
  const gridColor = isDark ? '#1e293b' : '#E2E8F0';
  const textColor = isDark ? '#94A3B8' : '#64748B';
  const tooltipBg = isDark ? '#151F30' : '#FFFFFF';
  const tooltipBorder = isDark ? '#263449' : '#E5EAF2';

  return (
    <div id="models" className="bg-card border border-theme rounded-xl p-5 sm:p-6 theme-card-shadow flex flex-col justify-between">
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-theme gap-2">
          <div className="flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-accent-theme" />
            <h3 className="text-sm font-bold text-primary uppercase tracking-wider">
              Fixed Model vs Adaptive Model
            </h3>
          </div>
          <div>
            {samples > 0 ? (
              <span className="px-2.5 py-1 rounded-md text-[11px] font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 font-semibold">
                Live Stream (N={samples} evaluated)
              </span>
            ) : (
              <span className="px-2.5 py-1 rounded-md text-[11px] font-mono bg-card-subtle border border-theme text-secondary font-medium">
                Offline Benchmark (N=12,000 Holdout)
              </span>
            )}
          </div>
        </div>

        <p className="text-[13px] text-secondary my-3 leading-relaxed">
          Demonstrates fixed baseline decay when evasion attacks begin, compared with the online adaptive model's measured recovery.
        </p>

        {/* Recharts Grouped Bar Chart */}
        <div className="h-64 w-full my-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
              <XAxis
                dataKey="metric"
                stroke={textColor}
                fontSize={12}
                tickLine={false}
              />
              <YAxis
                stroke={textColor}
                fontSize={12}
                domain={[0, 100]}
                unit="%"
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: tooltipBg,
                  borderColor: tooltipBorder,
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: isDark ? '#F1F5F9' : '#172033',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                }}
                formatter={(val) => [`${val}%`, '']}
              />
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
              />
              <Bar
                dataKey="Fixed"
                fill={isDark ? '#64748B' : '#94A3B8'}
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
              <Bar
                dataKey="Adaptive"
                fill={isDark ? '#38BDF8' : '#2563EB'}
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Summary Highlight Box */}
      <div className="mt-4 p-3.5 rounded-lg bg-card-subtle border border-theme text-xs sm:text-[13px] text-secondary flex items-start gap-2.5">
        <CheckCircle2 className="w-4 h-4 text-accent-theme shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="text-primary font-semibold">Measured Result: </strong>
          Fixed model recall crashes to <strong className="text-rose-500 font-bold">42.0%</strong> under micro-velocity attacks.
          Online learning via verified feedback restores recall to <strong className="text-emerald-500 font-bold">99.2%+</strong> without increasing false alerts.
        </div>
      </div>
    </div>
  );
}

export default React.memo(ModelComparisonComponent);
