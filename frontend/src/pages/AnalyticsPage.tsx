import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  FileSpreadsheet,
  RefreshCw,
  AlertTriangle,
  Users,
  Percent,
  DollarSign,
  Package,
  Layers,
  Clock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';
import { api } from '../services/api';
import { formatRupees, formatIndianNumber } from '../utils/format';
import { KpiCard } from '../components/shared/KpiCard';
import { TrendChart } from '../components/shared/TrendChart';

interface AnalyticsPageProps {
  currencySymbol?: string;
}

export const AnalyticsPage: React.FC<AnalyticsPageProps> = ({ currencySymbol = '₹' }) => {
  const [activeTab, setActiveTab] = useState<'demo' | 'live'>('demo');
  const [demoData, setDemoData] = useState<any | null>(null);
  const [liveData, setLiveData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [importing, setImporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDemo = async () => {
    try {
      const res = await api.getDemoAnalytics();
      setDemoData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load demo analytics');
    }
  };

  const fetchLive = async () => {
    try {
      const res = await api.getLiveAnalytics();
      setLiveData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load live analytics');
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchDemo(), fetchLive()]).finally(() => setLoading(false));
  }, []);

  const handleImportDemo = async () => {
    setImporting(true);
    try {
      const res = await api.importDemoAnalytics();
      if (res && res.data) {
        setDemoData(res.data);
      }
    } catch (err: any) {
      setError('Re-import error: ' + (err?.message || 'Unknown error'));
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-blue-600" />
            <span>Retail & Supply Analytics</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Compare offline demonstration data models with real point-of-sale store transactions.
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="flex items-center p-1 bg-slate-100 rounded-lg border border-slate-200 text-xs font-semibold self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('demo')}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === 'demo'
                ? 'bg-white text-slate-900 shadow-xs font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-amber-500" />
            <span>Demo Analytics</span>
            <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-100 text-amber-800">CSV</span>
          </button>
          <button
            onClick={() => {
              setActiveTab('live');
              fetchLive();
            }}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === 'live'
                ? 'bg-white text-slate-900 shadow-xs font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Live Sales & Ledger</span>
            <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-100 text-emerald-800">Live</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="font-bold underline text-[11px]">Dismiss</button>
        </div>
      )}

      {/* =========================================================================
          TAB 1: DEMO ANALYTICS (CSV COMPUTED)
          ========================================================================= */}
      {activeTab === 'demo' && demoData && (
        <div className="space-y-6 animate-fade-in">
          {/* Demo Data Notice Strip */}
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-start sm:items-center gap-2.5">
              <span className="px-2 py-0.5 rounded-full font-bold bg-amber-500 text-white text-[11px] uppercase tracking-wider shrink-0">
                Demo data
              </span>
              <div>
                <p className="font-semibold text-amber-900">
                  Data source: {demoData.badge} — Computed: {demoData.computed_at}
                </p>
                <p className="text-[11px] text-amber-700">
                  Loaded from files: {demoData.source_files?.join(', ') || 'backend/demo_data/*.csv'}. All figures computed dynamically.
                </p>
              </div>
            </div>

            <button
              onClick={handleImportDemo}
              disabled={importing}
              className="px-3 py-1.5 rounded-lg bg-white border border-amber-300 text-amber-900 hover:bg-amber-100 font-semibold flex items-center gap-1.5 shrink-0 transition-colors shadow-2xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${importing ? 'animate-spin' : ''}`} />
              <span>{importing ? 'Recomputing...' : 'Re-import CSVs'}</span>
            </button>
          </div>

          {/* Computed KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard
              label="Demo Gross Revenue"
              value={formatRupees(demoData.kpis.total_revenue_paise)}
              subtitle={`${demoData.kpis.total_transactions} transactions in CSV`}
              icon={<DollarSign className="w-4 h-4 text-emerald-600" />}
              isDemo={true}
              sourceLabel="backend/demo_data/retail_demo_sales.csv"
            />
            <KpiCard
              label="Avg Ticket Value"
              value={formatRupees(demoData.kpis.average_ticket_paise)}
              subtitle={`${demoData.kpis.total_units_sold} total units sold`}
              icon={<TrendingUp className="w-4 h-4 text-blue-600" />}
              isDemo={true}
              sourceLabel="Computed from demo CSV"
            />
            <KpiCard
              label="Gross Profit Margin"
              value={`${demoData.kpis.gross_profit_margin_pct}%`}
              subtitle="Weighted item margin"
              icon={<Percent className="w-4 h-4 text-purple-600" />}
              isDemo={true}
              sourceLabel="CSV item price vs cost"
            />
            <KpiCard
              label="Store Conversion Rate"
              value={`${demoData.kpis.conversion_rate_pct}%`}
              subtitle={`${demoData.kpis.pos_conversions} / ${demoData.kpis.total_footfall} visitors`}
              icon={<Users className="w-4 h-4 text-amber-600" />}
              isDemo={true}
              sourceLabel="store_footfall_demo.csv"
            />
          </div>

          {/* Category Breakdown & Shrinkage Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Category Performance */}
            <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Package className="w-4 h-4 text-blue-600" />
                  <span>Category Revenue Breakdown (Computed from CSV)</span>
                </h3>
                <span className="text-[11px] text-amber-700 font-mono bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  Demo data
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3 text-right">Units Sold</th>
                      <th className="py-2.5 px-3 text-right">Gross Sales</th>
                      <th className="py-2.5 px-3 text-right">% of Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(demoData.category_breakdown || []).map((cat: any) => {
                      const pct = demoData.kpis.total_revenue_paise > 0
                        ? ((cat.revenue_paise / demoData.kpis.total_revenue_paise) * 100).toFixed(1)
                        : '0.0';
                      return (
                        <tr key={cat.category} className="hover:bg-slate-50/60">
                          <td className="py-2.5 px-3 font-semibold text-slate-800">{cat.category}</td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">{cat.units}</td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                            {formatRupees(cat.revenue_paise)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-500">{pct}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Shrinkage & Loss Card */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span>Shrinkage & Spoilage Audit</span>
                </h3>
                <span className="text-[11px] text-amber-700 font-mono bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  Demo data
                </span>
              </div>

              <div className="p-3 bg-red-50/60 rounded-lg border border-red-100 flex items-center justify-between">
                <div>
                  <span className="text-[11px] text-red-600 block">Total Audited Loss</span>
                  <span className="text-lg font-bold font-mono text-red-700">
                    {formatRupees(demoData.kpis.shrinkage_loss_paise)}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[11px] text-red-600 block">Units Lost</span>
                  <span className="text-lg font-bold font-mono text-red-700">
                    {demoData.kpis.shrinkage_units_lost} units
                  </span>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                {(demoData.shrinkage_by_reason || []).map((sr: any) => (
                  <div key={sr.reason} className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                    <span className="font-semibold text-slate-700">{sr.reason}</span>
                    <div className="text-right font-mono">
                      <span className="text-slate-900 font-bold">{formatRupees(sr.loss_paise)}</span>
                      <span className="text-slate-400 text-[10px] ml-1.5">({sr.units} u)</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 2: LIVE SALES & LEDGER (ZERO SYNTHETIC DATA)
          ========================================================================= */}
      {activeTab === 'live' && liveData && (
        <div className="space-y-6 animate-fade-in">
          {/* Live Data Notice Strip */}
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded-full font-bold bg-emerald-600 text-white text-[11px] uppercase tracking-wider shrink-0 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Live Store Ledger
              </span>
              <div>
                <p className="font-semibold text-emerald-950">
                  Data source: {liveData.badge} — Synchronized: {liveData.computed_at}
                </p>
                <p className="text-[11px] text-emerald-800">
                  Real transactions created through POS scanner, dynamic UPI checkouts, and Rule 5 stock audit ledger.
                </p>
              </div>
            </div>

            <button
              onClick={fetchLive}
              className="px-3 py-1.5 rounded-lg bg-white border border-emerald-300 text-emerald-900 hover:bg-emerald-100 font-semibold flex items-center gap-1.5 shrink-0 transition-colors shadow-2xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Ledger</span>
            </button>
          </div>

          {/* Live KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KpiCard
              label="Real Store Revenue"
              value={formatRupees(liveData.kpis.total_revenue_paise)}
              subtitle={`${liveData.kpis.total_transactions} transactions settled`}
              icon={<DollarSign className="w-4 h-4 text-emerald-600" />}
              isDemo={false}
              sourceLabel="SQLite table 'sales'"
            />
            <KpiCard
              label="Live Units Sold"
              value={`${formatIndianNumber(liveData.kpis.total_units_sold)} units`}
              subtitle="Audited in inventory movements"
              icon={<Package className="w-4 h-4 text-blue-600" />}
              isDemo={false}
              sourceLabel="Live sales line items"
            />
            <KpiCard
              label="Average Checkout"
              value={formatRupees(liveData.kpis.avg_transaction_paise)}
              subtitle="Per physical transaction"
              icon={<TrendingUp className="w-4 h-4 text-purple-600" />}
              isDemo={false}
              sourceLabel="Live ledger average"
            />
          </div>

          {/* Real Transactions Ledger */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-600" />
                <span>Live Transaction Ledger (Recent 15 Transactions)</span>
              </h3>
              <span className="text-xs text-slate-500 font-mono">
                Source: Real SQLite records with exact timestamps
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3">SKU</th>
                    <th className="py-2.5 px-3">Product Name</th>
                    <th className="py-2.5 px-3 text-right">Qty</th>
                    <th className="py-2.5 px-3 text-right">Amount</th>
                    <th className="py-2.5 px-3">Mode</th>
                    <th className="py-2.5 px-3">UTR / Ref</th>
                    <th className="py-2.5 px-3">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(liveData.recent_transactions || []).map((tx: any) => (
                    <tr key={tx.id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-mono text-slate-500">{tx.timestamp}</td>
                      <td className="py-2.5 px-3 font-mono font-bold text-blue-700">{tx.sku}</td>
                      <td className="py-2.5 px-3 font-semibold text-slate-800">{tx.product_name}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-700">{tx.quantity}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                        {formatRupees(tx.total_paise)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                          {tx.payment_mode}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-500 text-[11px] truncate max-w-[140px]">
                        {tx.reference_id}
                      </td>
                      <td className="py-2.5 px-3 text-slate-500 text-[11px]">{tx.source}</td>
                    </tr>
                  ))}
                  {(!liveData.recent_transactions || liveData.recent_transactions.length === 0) && (
                    <tr>
                      <td colSpan={8} className="py-6 text-center text-slate-400">
                        No transactions yet in live store ledger.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Rule 5 Stock Audit Movements */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-600" />
                <span>Rule 5 Immutable Stock Deduction Audit Trail</span>
              </h3>
              <span className="text-xs text-slate-500 font-mono">
                Source: table 'inventory_movements'
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3">SKU</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3 text-right">Delta</th>
                    <th className="py-2.5 px-3 text-right">Balance After</th>
                    <th className="py-2.5 px-3">Reason</th>
                    <th className="py-2.5 px-3">Reference</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(liveData.recent_inventory_audit || []).map((m: any) => (
                    <tr key={m.id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-mono text-slate-500">{m.timestamp}</td>
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-700">{m.sku}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          m.movement_type === 'SALE' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'
                        }`}>
                          {m.movement_type}
                        </span>
                      </td>
                      <td className={`py-2.5 px-3 text-right font-mono font-bold ${
                        m.delta < 0 ? 'text-red-600' : 'text-emerald-600'
                      }`}>
                        {m.delta > 0 ? `+${m.delta}` : m.delta}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                        {m.balance_after}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">{m.reason}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-400 text-[11px] truncate max-w-[150px]">
                        {m.reference || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
