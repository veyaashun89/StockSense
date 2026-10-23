import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, AlertCircle } from 'lucide-react';

interface StockHealthBarProps {
  healthy: number;
  low: number;
  expiring: number;
  outOfStock: number;
  className?: string;
}

export const StockHealthBar: React.FC<StockHealthBarProps> = ({
  healthy,
  low,
  expiring,
  outOfStock,
  className = ''
}) => {
  const total = Math.max(1, healthy + low + expiring + outOfStock);

  const pHealthy = Math.round((healthy / total) * 100);
  const pLow = Math.round((low / total) * 100);
  const pExpiring = Math.round((expiring / total) * 100);
  const pOutOfStock = Math.max(0, 100 - (pHealthy + pLow + pExpiring));

  return (
    <div
      role="region"
      aria-label="Stock Health Distribution"
      className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 sm:p-5 shadow-xs ${className}`}
    >
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Catalog Health & Availability
        </span>
        <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
          {total} Total SKUs
        </span>
      </div>

      {/* Stacked Bar with WCAG contrast */}
      <div
        className="w-full h-3 rounded-full overflow-hidden flex bg-slate-100 dark:bg-slate-800"
        role="progressbar"
        aria-valuenow={pHealthy}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {pHealthy > 0 && (
          <div
            style={{ width: `${pHealthy}%` }}
            className="bg-emerald-500 transition-all duration-500"
            title={`Healthy: ${healthy} items (${pHealthy}%)`}
          />
        )}
        {pLow > 0 && (
          <div
            style={{ width: `${pLow}%` }}
            className="bg-amber-500 transition-all duration-500"
            title={`Low Stock: ${low} items (${pLow}%)`}
          />
        )}
        {pExpiring > 0 && (
          <div
            style={{ width: `${pExpiring}%` }}
            className="bg-orange-500 transition-all duration-500"
            title={`Expiring: ${expiring} items (${pExpiring}%)`}
          />
        )}
        {pOutOfStock > 0 && (
          <div
            style={{ width: `${pOutOfStock}%` }}
            className="bg-rose-500 transition-all duration-500"
            title={`Out of Stock: ${outOfStock} items (${pOutOfStock}%)`}
          />
        )}
      </div>

      {/* Legend with Icons, Color, and Explicit Text */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3.5 pt-3 border-t border-slate-100 dark:border-slate-800/80 text-xs">
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          <span className="text-slate-600 dark:text-slate-400">Healthy:</span>
          <span className="font-bold tabular-nums text-slate-900 dark:text-white">{healthy}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" aria-hidden="true" />
          <span className="text-slate-600 dark:text-slate-400">Low Stock:</span>
          <span className="font-bold tabular-nums text-slate-900 dark:text-white">{low}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-orange-600 dark:text-orange-400" aria-hidden="true" />
          <span className="text-slate-600 dark:text-slate-400">Expiring:</span>
          <span className="font-bold tabular-nums text-slate-900 dark:text-white">{expiring}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" aria-hidden="true" />
          <span className="text-slate-600 dark:text-slate-400">Out of Stock:</span>
          <span className="font-bold tabular-nums text-rose-600 dark:text-rose-400">{outOfStock}</span>
        </div>
      </div>
    </div>
  );
};
