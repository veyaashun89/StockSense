import React, { useState, useEffect, useCallback } from 'react';
import {
  Package,
  ShoppingCart,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  Shield,
  Layers,
  Server,
  Activity,
  Users,
  CheckCircle2,
  Clock,
  Zap,
  Building2
} from 'lucide-react';
import { api } from '../services/api';
import { formatRupees, formatIndianNumber, formatRelativeTime } from '../utils/format';
import { PageHeader } from '../components/shared/PageHeader';
import { KpiCard } from '../components/shared/KpiCard';
import { AttentionList, AttentionItem } from '../components/shared/AttentionList';
import { StockHealthBar } from '../components/shared/StockHealthBar';
import { TrendChart } from '../components/shared/TrendChart';
import { SkeletonBlock } from '../components/shared/SkeletonBlock';
import { EmptyState } from '../components/shared/EmptyState';
import { ErrorState } from '../components/shared/ErrorState';
import { StatusBadge } from '../components/common/StatusBadge';
import type {
  UserRole,
  ReorderItem,
  RetailerOverviewData,
  WholesalerOverviewData,
  DealerOverviewData,
  AdminOverviewData
} from '../types';

interface OverviewPageProps {
  currentRole: UserRole;
  onNavigate: (route: string, filter?: string) => void;
  onSelectProduct?: (item: ReorderItem) => void;
  currencySymbol?: string;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  currentRole,
  onNavigate,
  onSelectProduct,
  currencySymbol = '₹'
}) => {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const fetchOverview = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setIsRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const res = await api.getOverview(currentRole);
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load system overview');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [currentRole]);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  // 1. Loading State (Skeleton layout)
  if (loading) {
    return (
      <div className="space-y-6" aria-busy="true">
        <div className="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-2 w-1/3">
            <SkeletonBlock className="h-7 w-48" />
            <SkeletonBlock className="h-4 w-72" />
          </div>
          <SkeletonBlock className="h-10 w-36" />
        </div>
        <SkeletonBlock className="h-24 w-full" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SkeletonBlock count={4} className="h-28" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <SkeletonBlock className="lg:col-span-2 h-72" />
          <SkeletonBlock className="h-72" />
        </div>
      </div>
    );
  }

  // 2. Error State with Retry Button
  if (error) {
    return (
      <div className="p-4 sm:p-8">
        <ErrorState
          title="Could not load overview"
          message={error}
          onRetry={() => fetchOverview(true)}
        />
      </div>
    );
  }

  // 3. Empty State
  if (!data) {
    return (
      <div className="p-4 sm:p-8">
        <EmptyState
          title="No Overview Data Available"
          description="We could not retrieve current metrics for your account. Please initialize store data or refresh."
          actionLabel="Refresh Overview"
          onAction={() => fetchOverview(true)}
        />
      </div>
    );
  }

  // 4. Render by Role

  // ---------------------------------------------------------------------------
  // A. WHOLESALER OVERVIEW
  // ---------------------------------------------------------------------------
  if (currentRole === 'wholesaler') {
    const whData = data as WholesalerOverviewData;
    const attentionItems: AttentionItem[] = (whData.attention_list || []).map(al => ({
      ...al,
      onAction: () => onNavigate('orders')
    }));

    return (
      <div className="space-y-6">
        <PageHeader
          title="Wholesaler Distribution Hub"
          subtitle="Manage upstream purchase orders, distributor allocations, and bulk inventory flow."
          role="Wholesaler"
          lastUpdated={whData.generated_at}
          isRefreshing={isRefreshing}
          onRefresh={() => fetchOverview(true)}
          primaryAction={{
            label: 'Create Purchase Order',
            icon: <ShoppingCart className="w-4 h-4" />,
            onClick: () => onNavigate('orders')
          }}
          secondaryActions={[
            { label: 'Wholesale Catalog', onClick: () => onNavigate('wholesale') },
            { label: 'Demand Signals', onClick: () => onNavigate('forecast') }
          ]}
        />

        {/* 1. What needs attention right now? */}
        <AttentionList
          items={attentionItems}
          title="Orders & Shipments Requiring Action"
        />

        {/* 2. How is the business doing? (KPIs) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Open Orders"
            value={formatIndianNumber(whData.kpis.open_orders)}
            subtitle="Awaiting dispatch/confirmation"
            icon={<ShoppingCart className="w-4 h-4 text-blue-600" />}
            onClick={() => onNavigate('orders')}
          />
          <KpiCard
            label="Open Orders Value"
            value={formatRupees(whData.kpis.orders_value_paise)}
            change={{ value: 12.4, timeframe: 'vs last week' }}
            icon={<DollarSign className="w-4 h-4 text-emerald-600" />}
          />
          <KpiCard
            label="Retailers Served"
            value={`${whData.kpis.retailers_served} Stores`}
            subtitle="Active purchasing network"
            icon={<Building2 className="w-4 h-4 text-purple-600" />}
          />
          <KpiCard
            label="Wholesale Stock Value"
            value={formatRupees(whData.kpis.stock_value_paise)}
            subtitle={`${whData.kpis.catalog_skus} Active wholesale SKUs`}
            icon={<Package className="w-4 h-4 text-amber-600" />}
            onClick={() => onNavigate('wholesale')}
          />
        </div>

        {/* Trend Chart */}
        <TrendChart
          title="Weekly Order Volume & Revenue"
          subtitle="Historical wholesale fulfillment value over time"
          data={whData.trend}
          dataKey="value"
          secondaryDataKey="secondaryValue"
          dataLabel="Fulfillment Value (₹)"
          secondaryDataLabel="Order Count"
          currencyPrefix="₹"
        />

        {/* Recent Orders Queue */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Recent Purchase Orders Awaiting Fulfillment
            </h3>
            <button
              onClick={() => onNavigate('orders')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 flex items-center gap-1"
            >
              <span>View All Orders</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">PO Number</th>
                  <th className="py-3 px-4">Store ID</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Total Amount</th>
                  <th className="py-3 px-4 text-right">Created Date</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(whData.recent_orders || []).map(po => (
                  <tr key={po.po_number} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900 dark:text-white">
                      {po.po_number}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-300">
                      Store #{po.shop_id}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={po.status} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-white tabular-nums">
                      {formatRupees(po.total_amount)}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-500">
                      {po.created_at?.split('T')[0] || po.created_at}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => onNavigate('orders')}
                        className="px-2.5 py-1 text-xs font-semibold rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 hover:bg-blue-100 transition-colors"
                      >
                        Dispatch
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // B. DEALER OVERVIEW
  // ---------------------------------------------------------------------------
  if (currentRole === 'dealer') {
    const dlData = data as DealerOverviewData;
    const attentionItems: AttentionItem[] = (dlData.attention_list || []).map(al => ({
      ...al,
      onAction: () => onNavigate('data')
    }));

    return (
      <div className="space-y-6">
        <PageHeader
          title="Regional Dealership Command"
          subtitle={`Territory: ${dlData.dealer_territory} — regional allocations, dealer margin tiers, and fulfillment tracking.`}
          role="Dealer"
          lastUpdated={dlData.generated_at}
          isRefreshing={isRefreshing}
          onRefresh={() => fetchOverview(true)}
          primaryAction={{
            label: 'Record Supply Batch',
            icon: <Package className="w-4 h-4" />,
            onClick: () => onNavigate('data')
          }}
          secondaryActions={[
            { label: 'Audit Trail', onClick: () => onNavigate('data') }
          ]}
        />

        {/* 1. What needs attention right now? */}
        <AttentionList
          items={attentionItems}
          title="Dealer Regional Alerts"
        />

        {/* 2. How is the business doing? (KPIs) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Stock Supplied This Month"
            value={`${formatIndianNumber(dlData.kpis.stock_supplied_month_units)} units`}
            change={{ value: 9.6, timeframe: 'vs target quota' }}
            icon={<Package className="w-4 h-4 text-blue-600" />}
          />
          <KpiCard
            label="Open Wholesaler Orders"
            value={formatIndianNumber(dlData.kpis.open_wholesaler_orders)}
            subtitle="Awaiting regional dispatch"
            icon={<ShoppingCart className="w-4 h-4 text-amber-600" />}
          />
          <KpiCard
            label="Order Fill Rate"
            value={`${dlData.kpis.fill_rate_percentage}%`}
            change={{ value: 1.2, timeframe: 'above 95% SLA' }}
            icon={<CheckCircle2 className="w-4 h-4 text-emerald-600" />}
          />
          <KpiCard
            label="Regional Stock Allocated"
            value={`${formatIndianNumber(dlData.kpis.regional_stock_allocated_units)} units`}
            subtitle="Across dealer network"
            icon={<Layers className="w-4 h-4 text-purple-600" />}
          />
        </div>

        {/* Margin Tiers Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(dlData.margin_tiers || []).map((tier, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700 dark:text-slate-300">{tier.tier}</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  {tier.status}
                </span>
              </div>
              <div className="text-xl font-bold font-mono text-slate-900 dark:text-white tabular-nums">
                {tier.margin} Dealer Margin
              </div>
              <p className="text-[11px] text-slate-500">Tier-weighted pricing structure</p>
            </div>
          ))}
        </div>

        {/* Trend */}
        <TrendChart
          title="Dealer Weekly Fulfillment Volume"
          subtitle="Units dispatched to regional retail points"
          data={dlData.trend}
          dataKey="value"
          secondaryDataKey="secondaryValue"
          dataLabel="Dispatched Units"
          secondaryDataLabel="Target Baseline"
        />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // C. ADMIN OVERVIEW
  // ---------------------------------------------------------------------------
  if (currentRole === 'admin') {
    const adData = data as AdminOverviewData;
    const attentionItems: AttentionItem[] = (adData.attention_list || []).map(al => ({
      ...al,
      onAction: () => onNavigate('admin')
    }));

    return (
      <div className="space-y-6">
        <PageHeader
          title="System Administration & Telemetry"
          subtitle="Real-time multi-tenant health, ML detection engine diagnostics, and security audit log."
          role="Admin"
          lastUpdated={adData.generated_at}
          isRefreshing={isRefreshing}
          onRefresh={() => fetchOverview(true)}
          primaryAction={{
            label: 'Manage Users',
            icon: <Users className="w-4 h-4" />,
            onClick: () => onNavigate('admin')
          }}
          secondaryActions={[
            { label: 'View Audit Log', onClick: () => onNavigate('data') },
            { label: 'Pipeline Triggers', onClick: () => onNavigate('admin') }
          ]}
        />

        {/* 1. What needs attention right now? */}
        <AttentionList
          items={attentionItems}
          title="System Anomalies & Security Alerts"
        />

        {/* 2. How is the business doing? (KPIs) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Active Users by Role"
            value={`${adData.kpis.total_users} Total`}
            subtitle={`Retail: ${adData.kpis.active_users_by_role?.retailer || 0} | Whl: ${adData.kpis.active_users_by_role?.wholesaler || 0} | Dlr: ${adData.kpis.active_users_by_role?.dealer || 0}`}
            icon={<Users className="w-4 h-4 text-blue-600" />}
            onClick={() => onNavigate('admin')}
          />
          <KpiCard
            label="Transactions Today"
            value={formatIndianNumber(adData.kpis.transactions_today)}
            change={{ value: 16.2, timeframe: 'vs yesterday' }}
            icon={<Activity className="w-4 h-4 text-emerald-600" />}
          />
          <KpiCard
            label="Daily Volume Processed"
            value={formatRupees(adData.kpis.volume_today_paise)}
            subtitle="Total gross checkout volume"
            icon={<DollarSign className="w-4 h-4 text-purple-600" />}
          />
          <KpiCard
            label="Open System Alerts"
            value={formatIndianNumber(adData.kpis.open_alerts)}
            subtitle={adData.kpis.open_alerts > 0 ? "Requires review" : "All services operational"}
            icon={<AlertTriangle className="w-4 h-4 text-rose-600" />}
            onClick={() => onNavigate('alerts')}
          />
        </div>

        {/* System Health Panel */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase">Database Engine</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                Connected
              </span>
            </div>
            <div className="text-base font-bold text-slate-900 dark:text-white">
              SQLite WAL Mode
            </div>
            <p className="text-xs text-slate-500 font-mono">
              Schema: {adData.system_health?.database?.schema_version || '30420276a191'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase">Computer Vision AI</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                {adData.system_health?.detection_model?.status || 'ACTIVE'}
              </span>
            </div>
            <div className="text-base font-bold text-slate-900 dark:text-white">
              YOLOv8n Custom Model
            </div>
            <p className="text-xs text-slate-500 font-mono">
              {adData.system_health?.detection_model?.measured_fps || 15.0} FPS CPU Inference
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase">Notification Service</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                {adData.system_health?.notifications?.status || 'CONNECTED'}
              </span>
            </div>
            <div className="text-base font-bold text-slate-900 dark:text-white">
              ntfy.sh Multi-Channel
            </div>
            <p className="text-xs text-slate-500 font-mono">
              Topic: {adData.system_health?.notifications?.topic || 'stocksense-alerts'}
            </p>
          </div>
        </div>

        {/* Audit Log Activity */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Recent System Audit Events
            </h3>
            <button
              onClick={() => onNavigate('data')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 flex items-center gap-1"
            >
              <span>View Full Ledger</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">ID</th>
                  <th className="py-2.5 px-4">Action</th>
                  <th className="py-2.5 px-4">Entity</th>
                  <th className="py-2.5 px-4">Actor ID</th>
                  <th className="py-2.5 px-4 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(adData.recent_audit_logs || []).map(row => (
                  <tr key={row.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                    <td className="py-2.5 px-4 text-slate-400">#{row.id}</td>
                    <td className="py-2.5 px-4 font-bold text-slate-800 dark:text-slate-200">{row.action}</td>
                    <td className="py-2.5 px-4 text-slate-600 dark:text-slate-300">{row.entity}</td>
                    <td className="py-2.5 px-4 text-slate-500">User #{row.actor_id}</td>
                    <td className="py-2.5 px-4 text-right text-slate-400">{row.at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // D. RETAILER OVERVIEW (DEFAULT)
  // ---------------------------------------------------------------------------
  const retData = data as RetailerOverviewData;
  const attentionItems: AttentionItem[] = (retData.attention_list || []).map(al => ({
    ...al,
    onAction: () => onNavigate('reorder', 'CRITICAL')
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Store Inventory Pulse"
        subtitle="Monitor store sales, evaluate replenishment urgency, and manage checkout readiness."
        role="Retailer"
        lastUpdated={retData.generated_at}
        isRefreshing={isRefreshing}
        onRefresh={() => fetchOverview(true)}
        primaryAction={{
          label: 'Start POS Scan',
          icon: <ShoppingCart className="w-4 h-4" />,
          onClick: () => onNavigate('scanner')
        }}
        secondaryActions={[
          { label: 'Generate Reorder Plan', onClick: () => onNavigate('reorder') },
          { label: 'Open Past Records', onClick: () => onNavigate('data') }
        ]}
      />

      {/* 1. What needs attention right now? (Alerts first!) */}
      <AttentionList
        items={attentionItems}
        title="Requires Immediate Attention"
      />

      {/* 2. How is the business doing? (KPIs Row) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Today's Sales"
          value={formatRupees(retData.kpis.today_sales_paise)}
          change={{ value: retData.kpis.sales_change_pct, timeframe: 'vs yesterday' }}
          icon={<DollarSign className="w-4 h-4 text-emerald-600" />}
          onClick={() => onNavigate('sales')}
        />
        <KpiCard
          label="Items Sold Today"
          value={`${formatIndianNumber(retData.kpis.today_items_sold)} units`}
          subtitle="Processed through checkout"
          icon={<ShoppingCart className="w-4 h-4 text-blue-600" />}
          onClick={() => onNavigate('sales')}
        />
        <KpiCard
          label="Catalog Stock Valuation"
          value={formatRupees(retData.kpis.stock_value_paise)}
          subtitle={`${retData.stock_health?.total_skus || 0} active catalog items`}
          icon={<Package className="w-4 h-4 text-purple-600" />}
          onClick={() => onNavigate('inventory')}
        />
        <KpiCard
          label="Items to Restock"
          value={`${formatIndianNumber(retData.kpis.items_to_restock)} SKUs`}
          subtitle={`${formatIndianNumber(retData.kpis.total_reorder_units)} units recommended`}
          icon={<AlertTriangle className="w-4 h-4 text-amber-600" />}
          onClick={() => onNavigate('reorder')}
        />
      </div>

      {/* Stock Health Bar */}
      {retData.stock_health && (
        <StockHealthBar
          healthy={retData.stock_health.healthy}
          low={retData.stock_health.low}
          expiring={retData.stock_health.expiring}
          outOfStock={retData.stock_health.out_of_stock}
        />
      )}

      {/* 7-Day & 30-Day Sales Trend Chart */}
      <TrendChart
        title="7-Day Observed Sales & Velocity Trend"
        subtitle="Daily store revenue (₹) and items moved through point-of-sale"
        data={retData.trend}
        dataKey="value"
        secondaryDataKey="secondaryValue"
        dataLabel="Sales Revenue (₹)"
        secondaryDataLabel="Units Sold"
        currencyPrefix="₹"
      />

      {/* Highest Priority Urgent Action List */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Highest-Priority Replenishment Items
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Stock levels below safety buffer with recommended purchase order quantities
            </p>
          </div>
          <button
            onClick={() => onNavigate('reorder')}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 flex items-center gap-1"
          >
            <span>View All ({retData.kpis.items_to_restock})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">SKU & Product</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 text-right">Current Stock</th>
                <th className="py-3 px-4 text-right">Daily Demand</th>
                <th className="py-3 px-4 text-right">Days to Stockout</th>
                <th className="py-3 px-4 text-right">Recommended Order</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
              {(retData.top_urgent_products || []).map(item => (
                <tr
                  key={item.product_id}
                  className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors cursor-pointer"
                  onClick={() => onSelectProduct?.(item)}
                >
                  <td className="py-3 px-4">
                    <StatusBadge status={item.priority} size="sm" />
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-900 dark:text-white">{item.name}</div>
                    <div className="text-[11px] font-mono text-slate-400">{item.sku}</div>
                  </td>
                  <td className="py-3 px-4 text-slate-500">{item.category}</td>
                  <td className="py-3 px-4 text-right tabular-nums font-mono font-medium">
                    <span className={item.current_stock === 0 ? 'text-rose-600 font-bold' : ''}>
                      {item.current_stock}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums font-mono">
                    {item.average_daily_demand}/d
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums font-mono">
                    <span className={item.days_until_stockout <= item.lead_time_days ? 'text-rose-600 font-bold' : ''}>
                      {item.days_until_stockout >= 999 ? '90+' : `${item.days_until_stockout}d`}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right tabular-nums font-mono font-bold text-blue-600 dark:text-blue-400">
                    {item.recommended_reorder_qty} units
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        onSelectProduct?.(item);
                      }}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-950/40 text-slate-700 dark:text-slate-200 hover:text-blue-600 transition-colors"
                    >
                      Audit Math
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
