import React from 'react';
import { RefreshCw, Play, Clock, Bell, LogOut, Shield, User as UserIcon } from 'lucide-react';
import { UserRole, User } from '../../types';

interface TopbarProps {
  lastUpdated?: string;
  onRefresh?: () => void;
  onGeneratePlan?: () => void;
  isRefreshing?: boolean;
  currentRole: UserRole;
  currentUser?: User | null;
  onLogout?: () => void;
  openAlertsCount?: number;
  onNavigateAlerts?: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  lastUpdated,
  onRefresh,
  onGeneratePlan,
  isRefreshing = false,
  currentRole,
  currentUser,
  onLogout,
  openAlertsCount = 0,
  onNavigateAlerts
}) => {
  const roleStyles: Record<string, { bg: string; text: string; border: string }> = {
    retailer: {
      bg: 'bg-blue-50 dark:bg-blue-950/50',
      text: 'text-blue-700 dark:text-blue-300',
      border: 'border-blue-200 dark:border-blue-800'
    },
    wholesaler: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/50',
      text: 'text-emerald-700 dark:text-emerald-300',
      border: 'border-emerald-200 dark:border-emerald-800'
    },
    admin: {
      bg: 'bg-rose-50 dark:bg-rose-950/50',
      text: 'text-rose-700 dark:text-rose-300',
      border: 'border-rose-200 dark:border-rose-800'
    },
    dealer: {
      bg: 'bg-purple-50 dark:bg-purple-950/50',
      text: 'text-purple-700 dark:text-purple-300',
      border: 'border-purple-200 dark:border-purple-800'
    }
  };

  const currentRoleStyle = roleStyles[currentRole.toLowerCase()] || roleStyles.retailer;
  const initial = currentUser?.name ? currentUser.name.charAt(0).toUpperCase() : currentRole.charAt(0).toUpperCase();

  return (
    <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 sm:px-6 flex items-center justify-between shrink-0 sticky top-0 z-20 shadow-xs">
      {/* Left Status & System Health Indicator */}
      <div className="flex items-center gap-3">
        <span className="flex h-2.5 w-2.5 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
        </span>
        <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 hidden sm:inline">
          StockSense Intelligence
        </span>
        <span className="text-slate-300 dark:text-slate-700 hidden sm:inline">|</span>
        <span className="text-xs text-slate-500 dark:text-slate-400 hidden md:inline flex items-center gap-1">
          <Clock className="w-3.5 h-3.5 text-slate-400 inline" />{' '}
          {lastUpdated ? `${new Date(lastUpdated).toLocaleTimeString()}` : 'System Active'}
        </span>
      </div>

      {/* Right Controls: User Identity, Alert Bell, Actions, Logout */}
      <div className="flex items-center gap-3">
        {/* User Identity & Role Badge (No arbitrary role switching) */}
        <div className="flex items-center gap-2 pl-2">
          <div className="w-7 h-7 rounded-full bg-blue-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
            {initial}
          </div>
          <div className="hidden sm:block text-left">
            <div className="text-xs font-bold text-slate-900 dark:text-white leading-tight truncate max-w-[140px]">
              {currentUser?.name || 'Authenticated User'}
            </div>
            <div className="flex items-center gap-1 mt-0.5">
              <span
                className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded border ${currentRoleStyle.bg} ${currentRoleStyle.text} ${currentRoleStyle.border}`}
              >
                {currentRole}
              </span>
            </div>
          </div>
        </div>

        {/* Alert Bell */}
        {onNavigateAlerts && (
          <button
            onClick={onNavigateAlerts}
            className="relative p-2 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="View Automated Alerts"
            aria-label="View Automated Alerts"
          >
            <Bell className="w-4 h-4" />
            {openAlertsCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-red-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-pulse">
                {openAlertsCount > 9 ? '9+' : openAlertsCount}
              </span>
            )}
          </button>
        )}

        {/* Refresh Button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
            title="Reload current data"
            aria-label="Reload current data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-600' : 'text-slate-500'}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        )}

        {/* Primary Action (for retailer) */}
        {onGeneratePlan && currentRole === 'retailer' && (
          <button
            onClick={onGeneratePlan}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-bold shadow-sm shadow-blue-500/20 hover:bg-blue-700 transition-colors"
          >
            <Play className="w-3.5 h-3.5 fill-white" />
            <span className="hidden sm:inline">Generate Plan</span>
          </button>
        )}

        {/* Logout Button */}
        {onLogout && (
          <button
            onClick={onLogout}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-950/30 text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
            title="Sign Out of Session"
            aria-label="Sign Out of Session"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Sign Out</span>
          </button>
        )}
      </div>
    </header>
  );
};
