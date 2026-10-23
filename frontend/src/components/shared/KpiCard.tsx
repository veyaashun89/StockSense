import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface KpiCardProps {
  label: string;
  value: string | number;
  change?: {
    value: number; // percentage or delta, e.g. 12.5 or -4.2
    timeframe: string; // e.g. "vs yesterday", "vs last week"
  };
  sparklineData?: number[];
  icon?: React.ReactNode;
  subtitle?: string;
  onClick?: () => void;
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  change,
  sparklineData = [12, 18, 15, 24, 28, 22, 35],
  icon,
  subtitle,
  onClick,
  className = ''
}) => {
  const isPositive = change ? change.value > 0 : false;
  const isNegative = change ? change.value < 0 : false;
  const isZero = change ? change.value === 0 : true;

  // Mini Sparkline SVG
  const minVal = Math.min(...sparklineData);
  const maxVal = Math.max(...sparklineData, minVal + 1);
  const points = sparklineData
    .map((val, idx) => {
      const x = (idx / (sparklineData.length - 1)) * 60;
      const y = 20 - ((val - minVal) / (maxVal - minVal)) * 18;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div
      role={onClick ? 'button' : 'region'}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`${label}: ${value}`}
      onClick={onClick}
      onKeyDown={e => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
      className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 sm:p-5 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all ${
        onClick ? 'cursor-pointer active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600' : ''
      } ${className}`}
    >
      <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider">{label}</span>
        {icon && (
          <span className="w-8 h-8 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700/60 flex items-center justify-center text-slate-600 dark:text-slate-300">
            {icon}
          </span>
        )}
      </div>

      <div className="flex items-baseline justify-between gap-2 mt-1">
        <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tabular-nums tracking-tight">
          {value}
        </div>

        {/* Mini Sparkline Chart */}
        {sparklineData && sparklineData.length > 1 && (
          <svg className="w-16 h-6 overflow-visible opacity-75" aria-hidden="true">
            <polyline
              fill="none"
              stroke={isNegative ? '#EF4444' : isPositive ? '#10B981' : '#3B82F6'}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={points}
            />
          </svg>
        )}
      </div>

      {/* Delta vs Past with Arrow and Text */}
      <div className="mt-3 flex items-center justify-between text-xs pt-2 border-t border-slate-100 dark:border-slate-800/80">
        {change ? (
          <div className="flex items-center gap-1 font-medium">
            {isPositive && (
              <span className="inline-flex items-center text-emerald-600 dark:text-emerald-400 font-semibold gap-0.5">
                <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
                <span>+{Math.abs(change.value)}%</span>
              </span>
            )}
            {isNegative && (
              <span className="inline-flex items-center text-rose-600 dark:text-rose-400 font-semibold gap-0.5">
                <ArrowDownRight className="w-3.5 h-3.5" aria-hidden="true" />
                <span>-{Math.abs(change.value)}%</span>
              </span>
            )}
            {isZero && (
              <span className="inline-flex items-center text-slate-500 dark:text-slate-400 font-semibold gap-0.5">
                <Minus className="w-3.5 h-3.5" aria-hidden="true" />
                <span>0%</span>
              </span>
            )}
            <span className="text-slate-500 dark:text-slate-400 ml-1">{change.timeframe}</span>
          </div>
        ) : subtitle ? (
          <span className="text-slate-500 dark:text-slate-400 truncate">{subtitle}</span>
        ) : (
          <span className="text-slate-400 text-[11px]">Up to date</span>
        )}
      </div>
    </div>
  );
};
