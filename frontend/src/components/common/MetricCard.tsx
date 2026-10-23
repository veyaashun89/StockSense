import React, { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  badge?: string;
  variant?: 'default' | 'critical' | 'warning' | 'success';
  onClick?: () => void;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  badge,
  variant = 'default',
  onClick
}) => {
  let borderColor = 'border-slate-200';
  let iconBg = 'bg-slate-100 text-slate-700';

  if (variant === 'critical') {
    borderColor = 'border-red-200 hover:border-red-300';
    iconBg = 'bg-red-50 text-red-600';
  } else if (variant === 'warning') {
    borderColor = 'border-amber-200 hover:border-amber-300';
    iconBg = 'bg-amber-50 text-amber-600';
  } else if (variant === 'success') {
    borderColor = 'border-emerald-200 hover:border-emerald-300';
    iconBg = 'bg-emerald-50 text-emerald-600';
  }

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border ${borderColor} p-5 shadow-sm transition-all duration-150 ${
        onClick ? 'cursor-pointer hover:shadow-md' : ''
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</span>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${iconBg}`}>{icon}</div>
      </div>
      <div className="flex items-baseline gap-2">
        <div className="text-2xl font-bold text-slate-900 tabular-nums">{value}</div>
        {badge && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{badge}</span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
};
