import React, { useState } from 'react';
import { PageHeader } from '../components/shared/PageHeader';
import { KpiCard } from '../components/shared/KpiCard';
import { AttentionList, AttentionItem } from '../components/shared/AttentionList';
import { StockHealthBar } from '../components/shared/StockHealthBar';
import { TrendChart, TrendDataPoint } from '../components/shared/TrendChart';
import { SkeletonBlock } from '../components/shared/SkeletonBlock';
import { EmptyState } from '../components/shared/EmptyState';
import { ErrorState } from '../components/shared/ErrorState';
import { ShoppingCart, Package, DollarSign, Activity } from 'lucide-react';
import { formatRupees } from '../utils/format';

export const DevComponentsPage: React.FC = () => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedRole, setSelectedRole] = useState<'retailer' | 'wholesaler' | 'dealer' | 'admin'>('retailer');

  const sampleAlerts: AttentionItem[] = [
    {
      id: 1,
      severity: 'critical',
      title: 'Stockout Detected',
      affected: 'SKU-MLK-01',
      message: 'Amul Taaza Milk 1L has hit 0 units. Imminent sales blockage.',
      actionLabel: 'Reorder Now',
      onAction: () => alert('Action triggered for SKU-MLK-01')
    },
    {
      id: 2,
      severity: 'high',
      title: 'Expiring Batch Warning',
      affected: 'SKU-YGT-04',
      message: '18 units of Greek Yogurt expire in 48 hours. Discount recommended.',
      actionLabel: 'Mark Down',
      onAction: () => alert('Mark down action triggered')
    },
    {
      id: 3,
      severity: 'warning',
      title: 'Unfulfilled Purchase Order',
      affected: 'PO-2026-089',
      message: 'Supplier delivery delayed by 2 days past estimated arrival.',
      actionLabel: 'Trace Order',
      onAction: () => alert('Trace order action triggered')
    }
  ];

  const sampleTrend: TrendDataPoint[] = [
    { date: '17 Oct', value: 14200, secondaryValue: 12000 },
    { date: '18 Oct', value: 16800, secondaryValue: 13500 },
    { date: '19 Oct', value: 15400, secondaryValue: 14000 },
    { date: '20 Oct', value: 19200, secondaryValue: 15800 },
    { date: '21 Oct', value: 22100, secondaryValue: 17400 },
    { date: '22 Oct', value: 20500, secondaryValue: 18200 },
    { date: '23 Oct', value: 24800, secondaryValue: 21000 }
  ];

  return (
    <div className="space-y-8 p-4 sm:p-6 max-w-7xl mx-auto">
      <div className="bg-blue-50 dark:bg-blue-950/40 p-3 rounded-lg border border-blue-200 dark:border-blue-800 text-xs text-blue-800 dark:text-blue-300">
        <strong>Component Sandbox (/dev/components)</strong>: Verification gallery for shared design system components, states (loading, empty, error, data), and accessibility tokens.
      </div>

      {/* 1. PageHeader */}
      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">1. PageHeader Component</h2>
        <PageHeader
          title="Retailer Store Overview"
          subtitle="Real-time pulse of store operations, urgent reorder requirements, and POS checkout readiness."
          role={selectedRole}
          lastUpdated={new Date().toISOString()}
          isRefreshing={isRefreshing}
          onRefresh={() => {
            setIsRefreshing(true);
            setTimeout(() => setIsRefreshing(false), 800);
          }}
          primaryAction={{
            label: 'Start POS Scan',
            icon: <ShoppingCart className="w-4 h-4" />,
            onClick: () => alert('Primary action clicked!')
          }}
          secondaryActions={[
            { label: 'Export GST Summary', onClick: () => alert('Exporting GST...') },
            { label: 'View Audit Log', onClick: () => alert('Viewing Audit...') }
          ]}
        />
        <div className="flex gap-2 text-xs">
          {(['retailer', 'wholesaler', 'dealer', 'admin'] as const).map(r => (
            <button
              key={r}
              onClick={() => setSelectedRole(r)}
              className={`px-3 py-1 rounded-md border font-semibold capitalize ${
                selectedRole === r ? 'bg-blue-600 text-white border-blue-600' : 'bg-white dark:bg-slate-800 border-slate-200 text-slate-700 dark:text-slate-200'
              }`}
            >
              Role: {r}
            </button>
          ))}
        </div>
      </section>

      {/* 2. KpiCard */}
      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">2. KpiCard Component (Rule 4: Integer Paise)</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Today's Sales"
            value={formatRupees(2485000)} // ₹24,850.00
            change={{ value: 14.8, timeframe: 'vs yesterday' }}
            sparklineData={[12, 14, 18, 16, 22, 28, 35]}
            icon={<DollarSign className="w-4 h-4" />}
          />
          <KpiCard
            label="Items Sold Today"
            value="342 units"
            change={{ value: 8.2, timeframe: 'vs last week' }}
            sparklineData={[40, 45, 38, 52, 60, 58, 65]}
            icon={<ShoppingCart className="w-4 h-4" />}
          />
          <KpiCard
            label="Total Stock Valuation"
            value={formatRupees(18420000)} // ₹1,84,200.00
            change={{ value: -3.4, timeframe: 'depleted stock' }}
            sparklineData={[50, 48, 46, 42, 38, 35, 30]}
            icon={<Package className="w-4 h-4 text-rose-600" />}
          />
          <KpiCard
            label="Requires Restock"
            value="12 SKUs"
            subtitle="4 critical, 8 low threshold"
            icon={<Activity className="w-4 h-4 text-amber-600" />}
          />
        </div>
      </section>

      {/* 3. AttentionList */}
      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">3. AttentionList Component (Alerts First)</h2>
        <AttentionList items={sampleAlerts} title="Top Urgent Action Queue" />
      </section>

      {/* 4. StockHealthBar */}
      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">4. StockHealthBar Component</h2>
        <StockHealthBar healthy={68} low={18} expiring={6} outOfStock={4} />
      </section>

      {/* 5. TrendChart */}
      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">5. TrendChart Component (With Accessible Table Toggle)</h2>
        <TrendChart
          title="Daily Sales & Demand Velocity"
          subtitle="Observed revenue vs forecast benchmark"
          data={sampleTrend}
          dataKey="value"
          secondaryDataKey="secondaryValue"
          dataLabel="Actual Sales"
          secondaryDataLabel="Baseline Demand"
          currencyPrefix="₹"
        />
      </section>

      {/* 6. States: Loading, Empty, Error */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">6. Required Four States Verification</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-3">
            <span className="text-xs font-bold text-slate-500">State: Loading (Skeleton)</span>
            <SkeletonBlock count={3} className="h-6" />
            <SkeletonBlock count={1} className="h-20" />
          </div>

          <div>
            <EmptyState
              title="No Pending Orders"
              description="Your order queue is completely clear. No customer orders require fulfillment."
              actionLabel="Create Order"
              onAction={() => alert('Empty state CTA clicked')}
            />
          </div>

          <div>
            <ErrorState
              title="Connection Timeout"
              message="Could not reach the telemetry service. Verify network connectivity."
              onRetry={() => alert('Retry button clicked')}
            />
          </div>
        </div>
      </section>
    </div>
  );
};
