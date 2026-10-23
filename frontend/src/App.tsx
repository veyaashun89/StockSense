import React, { useState, useEffect } from 'react';
import { AppSidebar } from './components/layout/AppSidebar';
import { Topbar } from './components/layout/Topbar';
import { OverviewPage } from './pages/OverviewPage';
import { InventoryPage } from './pages/InventoryPage';
import { SalesPage } from './pages/SalesPage';
import { ForecastPage } from './pages/ForecastPage';
import { ReorderPlannerPage } from './pages/ReorderPlannerPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { DataManagementPage } from './pages/DataManagementPage';
import { AlertsPage } from './pages/AlertsPage';
import { PurchaseOrdersPage } from './pages/PurchaseOrdersPage';
import { WholesaleCatalogPage } from './pages/WholesaleCatalogPage';
import { AdminConsolePage } from './pages/AdminConsolePage';
import { ScannerPage } from './pages/ScannerPage';
import { RecordPage } from './pages/RecordPage';
import { DevComponentsPage } from './pages/DevComponentsPage';
import { LoginPage } from './pages/LoginPage';
import { RecommendationDrawer } from './components/common/RecommendationDrawer';
import type { DashboardData, ReorderItem, UserRole, User } from './types';
import { api, getStoredUser } from './services/api';

export default function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(() => getStoredUser());
  const [currentRoute, setCurrentRoute] = useState<string>('dashboard');
  const [currentRole, setCurrentRole] = useState<UserRole>(() => {
    const stored = getStoredUser();
    return stored?.role || 'retailer';
  });
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [currencySymbol, setCurrencySymbol] = useState<string>('₹');

  // Shared state for cross-page navigation
  const [selectedProductForDrawer, setSelectedProductForDrawer] = useState<ReorderItem | null>(null);
  const [initialPriorityFilter, setInitialPriorityFilter] = useState<string>('all');
  const [selectedForecastProductId, setSelectedForecastProductId] = useState<number | null>(null);

  const loadInitialData = async () => {
    try {
      const meRes = await api.getMe();
      if (meRes?.user?.role) {
        setCurrentRole(meRes.user.role);
        setCurrentUser(meRes.user);
      }
    } catch (e) {
      // If token expired or invalid, clear session
      if (!getStoredUser()) {
        setCurrentUser(null);
      }
    }
  };

  const loadDashboard = async (showRefresh = false) => {
    if (showRefresh) setIsRefreshing(true);
    else setLoadingDashboard(true);

    try {
      const [dash, settings] = await Promise.all([
        api.getDashboard(),
        api.getSettings().catch(() => ({ currency: '₹' }))
      ]);
      setDashboardData(dash);
      if (settings && settings.currency) {
        setCurrencySymbol(settings.currency);
      }
    } catch (err: any) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoadingDashboard(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (currentUser) {
      loadInitialData();
      loadDashboard();
    }

    const path = window.location.pathname.replace(/^\//, '');
    const validRoutes = [
      'dashboard', 'scanner', 'record', 'inventory', 'sales',
      'forecast', 'reorder', 'alerts', 'orders', 'wholesale',
      'admin', 'reports', 'settings', 'data', 'dev/components'
    ];
    if (validRoutes.includes(path)) {
      setCurrentRoute(path);
    }

    const onPop = () => {
      const p = window.location.pathname.replace(/^\//, '') || 'dashboard';
      if (validRoutes.includes(p)) {
        setCurrentRoute(p);
      }
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [currentUser?.id]);

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    setCurrentRoute('dashboard');
  };

  const handleLoginSuccess = (user: User) => {
    setCurrentUser(user);
    setCurrentRole(user.role);
    setCurrentRoute('dashboard');
    loadDashboard(true);
  };

  const handleNavigate = (route: string, filter?: string) => {
    if (filter) {
      setInitialPriorityFilter(filter);
    } else {
      setInitialPriorityFilter('all');
    }
    setCurrentRoute(route);
    try {
      window.history.pushState(null, '', `/${route === 'dashboard' ? '' : route}`);
    } catch (e) {
      // ignore
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectProduct = (item: ReorderItem) => {
    setSelectedProductForDrawer(item);
  };

  // If user is not authenticated, render dedicated multi-role Login Portal
  if (!currentUser) {
    return (
      <LoginPage
        onLoginSuccess={handleLoginSuccess}
        initialRole={currentRole}
      />
    );
  }

  return (
    <div className="flex h-screen bg-[#F7F9FC] font-sans text-slate-800 antialiased overflow-hidden">
      {/* Persistent Left Sidebar */}
      <AppSidebar
        currentRoute={currentRoute}
        onNavigate={handleNavigate}
        reorderBadgeCount={dashboardData?.summary?.critical_stockouts || 0}
        openAlertsCount={dashboardData?.open_alerts_count || 0}
        currentRole={currentRole}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        {/* Compact Top Navigation Bar with User Profile & Sign Out (No arbitrary role switching) */}
        <Topbar
          lastUpdated={dashboardData?.last_updated}
          onRefresh={() => loadDashboard(true)}
          onGeneratePlan={() => handleNavigate('reorder')}
          isRefreshing={isRefreshing}
          currentRole={currentRole}
          currentUser={currentUser}
          onLogout={handleLogout}
          openAlertsCount={dashboardData?.open_alerts_count || 0}
          onNavigateAlerts={() => handleNavigate('alerts')}
        />

        {/* Dynamic Route Content */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="max-w-7xl mx-auto">
            {currentRoute === 'dashboard' && (
              <OverviewPage
                currentRole={currentRole}
                onNavigate={handleNavigate}
                onSelectProduct={handleSelectProduct}
                currencySymbol={currencySymbol}
              />
            )}

            {currentRoute === 'scanner' && (
              <ScannerPage onNavigate={handleNavigate} />
            )}

            {currentRoute === 'record' && (
              <RecordPage onNavigate={handleNavigate} />
            )}

            {currentRoute === 'inventory' && (
              <InventoryPage currencySymbol={currencySymbol} />
            )}

            {currentRoute === 'sales' && (
              <SalesPage currencySymbol={currencySymbol} />
            )}

            {currentRoute === 'forecast' && (
              <ForecastPage initialProductId={selectedForecastProductId} />
            )}

            {currentRoute === 'reorder' && (
              <ReorderPlannerPage
                initialPriorityFilter={initialPriorityFilter}
                currencySymbol={currencySymbol}
                onNavigateToOrders={() => handleNavigate('orders')}
              />
            )}

            {currentRoute === 'alerts' && (
              <AlertsPage />
            )}

            {currentRoute === 'orders' && (
              <PurchaseOrdersPage />
            )}

            {currentRoute === 'wholesale' && (
              <WholesaleCatalogPage />
            )}

            {currentRoute === 'admin' && (
              <AdminConsolePage />
            )}

            {currentRoute === 'reports' && (
              <ReportsPage currencySymbol={currencySymbol} />
            )}

            {currentRoute === 'settings' && (
              <SettingsPage onSettingsUpdated={loadDashboard} />
            )}

            {currentRoute === 'data' && (
              <DataManagementPage onDataChanged={loadDashboard} />
            )}

            {currentRoute === 'dev/components' && (
              <DevComponentsPage />
            )}
          </div>
        </main>
      </div>

      {/* Global Detail Inspection Drawer */}
      <RecommendationDrawer
        item={selectedProductForDrawer}
        onClose={() => setSelectedProductForDrawer(null)}
        currencySymbol={currencySymbol}
      />
    </div>
  );
}
