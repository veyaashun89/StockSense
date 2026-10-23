import React from 'react';

interface StatusBadgeProps {
  status: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'HEALTHY' | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const norm = status.toUpperCase();

  let bg = 'bg-slate-100 text-slate-700 border-slate-200';
  let dot = 'bg-slate-500';
  let label = status;

  if (norm === 'CRITICAL') {
    bg = 'bg-red-50 text-red-700 border-red-200';
    dot = 'bg-red-600 animate-pulse';
    label = 'Critical Stockout';
  } else if (norm === 'HIGH') {
    bg = 'bg-amber-50 text-amber-800 border-amber-200';
    dot = 'bg-amber-600';
    label = 'High Urgency';
  } else if (norm === 'MEDIUM') {
    bg = 'bg-blue-50 text-blue-700 border-blue-200';
    dot = 'bg-blue-600';
    label = 'Reorder Needed';
  } else if (norm === 'HEALTHY') {
    bg = 'bg-emerald-50 text-emerald-800 border-emerald-200';
    dot = 'bg-emerald-600';
    label = 'Healthy';
  }

  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${bg} ${padding}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      <span>{label}</span>
    </span>
  );
};
