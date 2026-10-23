import React from 'react';
import { Calendar, FileSpreadsheet, AlertTriangle, CheckCircle2, Database } from 'lucide-react';
import { formatIndianNumber } from '../../utils/format';

interface DataOverviewStripProps {
  lastImport?: string;
  rowsRejected?: number;
  dateRange?: string;
  totalRecords?: number;
  className?: string;
}

export const DataOverviewStrip: React.FC<DataOverviewStripProps> = ({
  lastImport = 'Recent Batch',
  rowsRejected = 0,
  dateRange = 'Past 30 Days (Rolling)',
  totalRecords = 0,
  className = ''
}) => {
  return (
    <div
      role="region"
      aria-label="Data Ingestion & Ledger Overview Strip"
      className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 sm:p-4 shadow-xs flex flex-wrap items-center justify-between gap-4 ${className}`}
    >
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
          <FileSpreadsheet className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Last Pipeline Import
          </span>
          <p className="text-xs font-bold text-slate-900 dark:text-white truncate max-w-xs">
            {lastImport}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
          rowsRejected > 0 ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'
        }`}>
          {rowsRejected > 0 ? (
            <AlertTriangle className="w-4 h-4" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
          )}
        </div>
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Validation Status
          </span>
          <p className="text-xs font-bold text-slate-900 dark:text-white">
            {rowsRejected > 0 ? (
              <span className="text-amber-600 font-bold">{rowsRejected} Rows Rejected</span>
            ) : (
              <span className="text-emerald-600 font-bold">100% Clean Import (0 Rejections)</span>
            )}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
          <Calendar className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Date Scope
          </span>
          <p className="text-xs font-bold text-slate-900 dark:text-white">
            {dateRange}
          </p>
        </div>
      </div>

      {totalRecords > 0 && (
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center shrink-0">
            <Database className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Active Items
            </span>
            <p className="text-xs font-bold font-mono text-slate-900 dark:text-white tabular-nums">
              {formatIndianNumber(totalRecords)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
