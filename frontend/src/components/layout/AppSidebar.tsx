import React from 'react';
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  TrendingUp,
  ClipboardList,
  FileText,
  Settings,
  Database,
  Layers,
  Sparkles,
  Bell,
  Truck,
  Store,
  ShieldAlert,
  BarChart2,
  Scan,
  Eye
} from 'lucide-react';
import { UserRole } from '../../types';

interface AppSidebarProps {
  currentRoute: string;
  onNavigate: (route: string) => void;
  reorderBadgeCount?: number;
  openAlertsCount?: number;
  currentRole: UserRole;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({
  currentRoute,
  onNavigate,
  reorderBadgeCount = 0,
  openAlertsCount = 0,
  currentRole
}) => {
  // Define navigation lists based on role
  let operationsNav: Array<{ id: string; label: string; icon: any; badge?: number }> = [];
  let secondaryNav: Array<{ id: string; label: string; icon: any }> = [];

  if (currentRole === 'wholesaler') {
    operationsNav = [
      { id: 'dashboard', label: 'Wholesale Overview', icon: LayoutDashboard },
      { id: 'orders', label: 'Incoming Purchase Orders', icon: Truck },
      { id: 'wholesale', label: 'Wholesale Catalog', icon: Store },
      { id: 'analytics', label: 'Analytics & Demo Data', icon: BarChart2 },
      { id: 'reports', label: 'Reports', icon: FileText }
    ];
    secondaryNav = [
      { id: 'settings', label: 'Settings', icon: Settings },
      { id: 'data', label: 'Data Management', icon: Database }
    ];
  } else if (currentRole === 'admin') {
    operationsNav = [
      { id: 'dashboard', label: 'System Overview', icon: LayoutDashboard },
      { id: 'admin', label: 'Admin Console (RBAC)', icon: ShieldAlert },
      { id: 'data', label: 'Data & Pipeline', icon: Database },
      { id: 'analytics', label: 'Analytics & Demo Data', icon: BarChart2 },
      { id: 'reports', label: 'System Reports', icon: FileText }
    ];
    secondaryNav = [
      { id: 'settings', label: 'Global Settings', icon: Settings }
    ];
  } else {
    // Retailer (Default)
    operationsNav = [
      { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
      { id: 'scanner', label: 'AI Vision & POS Scanner', icon: Scan },
      { id: 'record', label: 'Live Record Analytics', icon: Eye },
      { id: 'analytics', label: 'Analytics & Demo Data', icon: BarChart2 },
      { id: 'inventory', label: 'Inventory', icon: Package },
      { id: 'sales', label: 'Sales & Imports', icon: ShoppingCart },
      { id: 'forecast', label: 'Demand Forecast', icon: TrendingUp },
      { id: 'reorder', label: 'Reorder Planner', icon: ClipboardList, badge: reorderBadgeCount },
      { id: 'alerts', label: 'Automated Alerts', icon: Bell, badge: openAlertsCount },
      { id: 'orders', label: 'Purchase Orders', icon: Truck },
      { id: 'reports', label: 'Reports', icon: FileText }
    ];
    secondaryNav = [
      { id: 'settings', label: 'Settings', icon: Settings },
      { id: 'data', label: 'Data Management & Pipeline', icon: Database }
    ];
  }

  return (
    <aside className="w-64 bg-[#172B4D] text-slate-300 flex flex-col shrink-0 min-h-screen border-r border-slate-800">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-700/60">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-tight flex items-center gap-1.5">
              StockSense <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-blue-500/30 text-blue-200 border border-blue-400/40">v2</span>
            </h1>
            <p className="text-[11px] text-slate-400 font-medium leading-none mt-0.5">Retail Inventory Intelligence</p>
          </div>
        </div>
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 py-4 px-3 space-y-6 overflow-y-auto">
        <div>
          <div className="px-3 mb-2 text-[10px] font-bold tracking-wider uppercase text-slate-400">
            {currentRole === 'wholesaler' ? 'Wholesale Suite' : currentRole === 'admin' ? 'Administration' : 'Retail Operations'}
          </div>
          <nav className="space-y-1">
            {operationsNav.map(item => {
              const Icon = item.icon;
              const isActive = currentRoute === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm font-semibold'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded-full tabular-nums ${
                        isActive ? 'bg-white text-blue-700' : 'bg-red-500 text-white'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {secondaryNav.length > 0 && (
          <div>
            <div className="px-3 mb-2 text-[10px] font-bold tracking-wider uppercase text-slate-400">
              System
            </div>
            <nav className="space-y-1">
              {secondaryNav.map(item => {
                const Icon = item.icon;
                const isActive = currentRoute === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-sm font-semibold'
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        )}
      </div>

      {/* Footer Info Box */}
      <div className="p-4 border-t border-slate-700/60 bg-slate-900/40">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>QUANTIX 2K26 • PS11</span>
        </div>
        <p className="text-[11px] text-slate-400 mt-1 capitalize font-medium">Logged in: {currentRole}</p>
      </div>
    </aside>
  );
};
