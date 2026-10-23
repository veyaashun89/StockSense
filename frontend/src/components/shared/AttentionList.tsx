import React from 'react';
import { AlertCircle, AlertTriangle, Info, ArrowRight, ShieldCheck } from 'lucide-react';

export interface AttentionItem {
  id: string | number;
  severity: 'critical' | 'high' | 'warning' | 'info';
  title: string;
  affected: string; // SKU, Item name, or Location
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

interface AttentionListProps {
  items: AttentionItem[];
  title?: string;
  maxItems?: number;
  className?: string;
}

export const AttentionList: React.FC<AttentionListProps> = ({
  items,
  title = 'Requires Immediate Attention',
  maxItems = 4,
  className = ''
}) => {
  const displayItems = items.slice(0, maxItems);

  if (displayItems.length === 0) {
    return (
      <div className={`p-4 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 flex items-center gap-3 ${className}`}>
        <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 flex items-center justify-center shrink-0">
          <ShieldCheck className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <h4 className="text-xs sm:text-sm font-bold text-emerald-900 dark:text-emerald-200">
            No Critical Blockers
          </h4>
          <p className="text-[11px] sm:text-xs text-emerald-700 dark:text-emerald-400">
            All inventory levels, active orders, and background operations are operating normally.
          </p>
        </div>
      </div>
    );
  }

  const severityConfig = {
    critical: {
      badgeBg: 'bg-rose-100 dark:bg-rose-950/60',
      badgeText: 'text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800',
      icon: <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" aria-hidden="true" />,
      label: 'Critical'
    },
    high: {
      badgeBg: 'bg-amber-100 dark:bg-amber-950/60',
      badgeText: 'text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800',
      icon: <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" aria-hidden="true" />,
      label: 'High'
    },
    warning: {
      badgeBg: 'bg-amber-50 dark:bg-amber-950/40',
      badgeText: 'text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800',
      icon: <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" aria-hidden="true" />,
      label: 'Warning'
    },
    info: {
      badgeBg: 'bg-blue-100 dark:bg-blue-950/60',
      badgeText: 'text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800',
      icon: <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" aria-hidden="true" />,
      label: 'Notice'
    }
  };

  return (
    <div className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs ${className}`}>
      <div className="px-4 py-3 bg-slate-50/80 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
          <span>{title}</span>
          <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
            {items.length}
          </span>
        </h3>
      </div>

      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {displayItems.map(item => {
          const cfg = severityConfig[item.severity] || severityConfig.warning;
          return (
            <div
              key={item.id}
              className="p-3.5 sm:p-4 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="flex items-start gap-3 min-w-0">
                <div className="mt-0.5">{cfg.icon}</div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-xs sm:text-sm text-slate-900 dark:text-white truncate">
                      {item.title}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-md border ${cfg.badgeBg} ${cfg.badgeText}`}
                    >
                      {cfg.label}
                    </span>
                    {item.affected && (
                      <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                        {item.affected}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">
                    {item.message}
                  </p>
                </div>
              </div>

              {item.actionLabel && item.onAction && (
                <button
                  onClick={item.onAction}
                  className="self-end sm:self-center shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-950/40 text-slate-700 dark:text-slate-200 hover:text-blue-600 dark:hover:text-blue-400 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 transition-colors"
                >
                  <span>{item.actionLabel}</span>
                  <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
