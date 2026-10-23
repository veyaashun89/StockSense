import React, { useState } from 'react';
import { RefreshCw, MoreVertical, Shield } from 'lucide-react';
import { formatRelativeTime } from '../../utils/format';

interface PageHeaderProps {
  title: string;
  subtitle: string;
  role: string;
  lastUpdated?: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  primaryAction?: {
    label: string;
    onClick: () => void;
    icon?: React.ReactNode;
  };
  secondaryActions?: Array<{
    label: string;
    onClick: () => void;
    icon?: React.ReactNode;
  }>;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  role,
  lastUpdated,
  onRefresh,
  isRefreshing = false,
  primaryAction,
  secondaryActions = []
}) => {
  const [menuOpen, setMenuOpen] = useState(false);

  const roleColors: Record<string, { bg: string; text: string; border: string }> = {
    retailer: { bg: 'bg-blue-50 dark:bg-blue-950/40', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800' },
    wholesaler: { bg: 'bg-emerald-50 dark:bg-emerald-950/40', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-800' },
    dealer: { bg: 'bg-purple-50 dark:bg-purple-950/40', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800' },
    admin: { bg: 'bg-rose-50 dark:bg-rose-950/40', text: 'text-rose-700 dark:text-rose-300', border: 'border-rose-200 dark:border-rose-800' },
  };

  const currentRoleStyle = roleColors[role.toLowerCase()] || roleColors.retailer;

  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200/60 dark:border-slate-800/60">
      <div className="space-y-1">
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            {title}
          </h1>
          <span
            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider border ${currentRoleStyle.bg} ${currentRoleStyle.text} ${currentRoleStyle.border}`}
          >
            <Shield className="w-3 h-3" aria-hidden="true" />
            <span>{role}</span>
          </span>
        </div>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-2xl">
          {subtitle}
        </p>
      </div>

      <div className="flex items-center gap-2.5 self-start md:self-center">
        {/* Last updated and refresh */}
        {onRefresh && (
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mr-1">
            <span className="hidden sm:inline">Updated: {formatRelativeTime(lastUpdated)}</span>
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              aria-label="Refresh page data"
              className="p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors disabled:opacity-50"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-600' : ''}`}
                aria-hidden="true"
              />
            </button>
          </div>
        )}

        {/* Primary Action Button (1 per page) */}
        {primaryAction && (
          <button
            onClick={primaryAction.onClick}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs sm:text-sm font-semibold shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors active:scale-98"
          >
            {primaryAction.icon}
            <span>{primaryAction.label}</span>
          </button>
        )}

        {/* Secondary Actions Menu */}
        {secondaryActions.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label="More actions"
              aria-expanded={menuOpen}
              className="p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors"
            >
              <MoreVertical className="w-4 h-4" aria-hidden="true" />
            </button>
            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 mt-1.5 w-48 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg py-1.5 z-30"
              >
                {secondaryActions.map((sec, idx) => (
                  <button
                    key={idx}
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(false);
                      sec.onClick();
                    }}
                    className="w-full text-left px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
                  >
                    {sec.icon}
                    <span>{sec.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
};
