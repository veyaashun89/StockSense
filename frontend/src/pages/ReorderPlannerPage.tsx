import React, { useState, useEffect } from 'react';
import {
  ClipboardList,
  Download,
  RefreshCw,
  Search,
  DollarSign,
  AlertTriangle,
  Clock,
  ShieldAlert,
  ShoppingCart,
  CheckCircle2,
  CheckSquare,
  Square
} from 'lucide-react';
import { api } from '../services/api';
import type { ReorderItem, ReorderPlanResponse } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { RecommendationDrawer } from '../components/common/RecommendationDrawer';
import { MetricCard } from '../components/common/MetricCard';

interface ReorderPlannerPageProps {
  initialPriorityFilter?: string;
  currencySymbol?: string;
  onNavigateToOrders?: () => void;
}

export const ReorderPlannerPage: React.FC<ReorderPlannerPageProps> = ({
  initialPriorityFilter = 'all',
  currencySymbol = '₹',
  onNavigateToOrders
}) => {
  const [plan, setPlan] = useState<ReorderPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState<string[]>([]);
  
  // Filters
  const [priorityFilter, setPriorityFilter] = useState(initialPriorityFilter);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [budgetCap, setBudgetCap] = useState<string>('');
  
  // Selection for PO creation
  const [selectedProductIds, setSelectedProductIds] = useState<Set<number>>(new Set());
  const [creatingPo, setCreatingPo] = useState(false);
  const [orderSuccessMsg, setOrderSuccessMsg] = useState<{ poNumber: string; count: number } | null>(null);

  // Selected drawer item
  const [selectedItem, setSelectedItem] = useState<ReorderItem | null>(null);
  const [isRecalculating, setIsRecalculating] = useState(false);

  const fetchPlan = async (isManualRecalc = false) => {
    if (isManualRecalc) setIsRecalculating(true);
    else setLoading(true);

    try {
      const budgetNum = budgetCap ? parseFloat(budgetCap) : undefined;
      const [planRes, catRes] = await Promise.all([
        api.getReorderPlan({
          category: selectedCategory,
          priority: priorityFilter,
          search,
          budget: budgetNum
        }),
        api.getCategories()
      ]);
      setPlan(planRes);
      setCategories(catRes);
      
      // Auto-select items that need reordering (> 0)
      const needReorder = new Set<number>();
      planRes.items.forEach(it => {
        if (it.recommended_reorder_qty > 0) needReorder.add(it.product_id);
      });
      setSelectedProductIds(needReorder);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
      setIsRecalculating(false);
    }
  };

  useEffect(() => {
    fetchPlan();
  }, [priorityFilter, selectedCategory, search]);

  const handleApplyBudget = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPlan(true);
  };

  const toggleSelectAll = () => {
    if (!plan) return;
    const itemsWithQty = plan.items.filter(i => i.recommended_reorder_qty > 0);
    if (selectedProductIds.size === itemsWithQty.length) {
      setSelectedProductIds(new Set());
    } else {
      setSelectedProductIds(new Set(itemsWithQty.map(i => i.product_id)));
    }
  };

  const toggleSelectOne = (productId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const next = new Set(selectedProductIds);
    if (next.has(productId)) next.delete(productId);
    else next.add(productId);
    setSelectedProductIds(next);
  };

  const handleCreatePurchaseOrder = async () => {
    if (!plan || selectedProductIds.size === 0) return;

    const selectedItems = plan.items
      .filter(it => selectedProductIds.has(it.product_id) && it.recommended_reorder_qty > 0)
      .map(it => ({
        product_id: it.product_id,
        sku: it.sku,
        product_name: it.name,
        quantity: it.recommended_reorder_qty,
        unit_cost: it.unit_cost || (it.purchase_cost / (it.recommended_reorder_qty || 1))
      }));

    if (selectedItems.length === 0) {
      alert('None of the selected products have a recommended reorder quantity greater than 0.');
      return;
    }

    try {
      setCreatingPo(true);
      const res = await api.createOrder({
        items: selectedItems,
        notes: `Automated replenishment PO generated from StockSense planner (${selectedItems.length} SKUs).`
      });
      setOrderSuccessMsg({
        poNumber: res.po_number,
        count: selectedItems.length
      });
      await fetchPlan(true);
    } catch (err: any) {
      alert(err?.message || 'Failed to generate purchase order');
    } finally {
      setCreatingPo(false);
    }
  };

  const cappedCount = plan?.items.filter(it => it.shelf_life_capped).length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-100 text-blue-800">
              Decision Workspace
            </span>
            <span className="text-xs text-slate-400">• Automated Replenishment</span>
          </div>
          <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight">Reorder Planner</h1>
          <p className="text-sm text-slate-500 mt-1">
            Prioritize store purchasing using daily demand forecasts, supplier lead times, and shelf-life constraints.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleCreatePurchaseOrder}
            disabled={creatingPo || selectedProductIds.size === 0}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <ShoppingCart className="w-3.5 h-3.5" />
            <span>{creatingPo ? 'Raising PO...' : `Create Purchase Order (${selectedProductIds.size})`}</span>
          </button>
          <a
            href={api.getReportDownloadUrl('reorder')}
            download
            className="px-3.5 py-2 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export CSV</span>
          </a>
          <button
            onClick={() => fetchPlan(true)}
            disabled={isRecalculating}
            className="px-3.5 py-2 rounded-lg bg-blue-600 text-white text-xs font-bold shadow-sm hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRecalculating ? 'animate-spin' : ''}`} />
            <span>{isRecalculating ? 'Recalculating...' : 'Recalculate'}</span>
          </button>
        </div>
      </div>

      {/* Purchase Order Success Toast */}
      {orderSuccessMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-medium flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <p className="font-bold text-sm">Purchase Order {orderSuccessMsg.poNumber} Created!</p>
              <p className="text-emerald-700 mt-0.5">
                Successfully created order with {orderSuccessMsg.count} line items. Inventory positions are updated to account for in-transit replenishments.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onNavigateToOrders && (
              <button
                onClick={onNavigateToOrders}
                className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700"
              >
                View in Orders
              </button>
            )}
            <button
              onClick={() => setOrderSuccessMsg(null)}
              className="p-1 text-emerald-700 hover:text-emerald-900 text-base"
            >
              &times;
            </button>
          </div>
        </div>
      )}

      {/* Summary KPI Cards Row (5 Cards) */}
      {plan?.summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
          <MetricCard
            title="Products to Reorder"
            value={plan.summary.products_requiring_reorder}
            subtitle={`${plan.summary.total_reorder_units.toLocaleString()} units needed`}
            icon={<ClipboardList className="w-4 h-4 text-blue-600" />}
            variant={plan.summary.products_requiring_reorder > 0 ? 'warning' : 'default'}
          />
          <MetricCard
            title="Critical Stockouts"
            value={plan.summary.critical_stockouts}
            subtitle="Immediate order needed"
            icon={<AlertTriangle className="w-4 h-4 text-red-600" />}
            variant={plan.summary.critical_stockouts > 0 ? 'critical' : 'default'}
            onClick={() => setPriorityFilter(priorityFilter === 'CRITICAL' ? 'all' : 'CRITICAL')}
          />
          <MetricCard
            title="Reorder Value"
            value={`${currencySymbol}${plan.summary.total_reorder_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            subtitle={plan.summary.budget_applied ? `Capped at ${currencySymbol}${plan.summary.budget_limit?.toLocaleString()}` : 'Total spend'}
            icon={<DollarSign className="w-4 h-4 text-emerald-600" />}
            variant="success"
          />
          <MetricCard
            title="Expiry Risks"
            value={plan.summary.expiry_risk_count}
            subtitle="Perishables at risk"
            icon={<Clock className="w-4 h-4 text-amber-600" />}
            variant={plan.summary.expiry_risk_count > 0 ? 'warning' : 'default'}
          />
          <MetricCard
            title="Shelf-Life Capped"
            value={cappedCount}
            subtitle="Cap bound order qty"
            icon={<ShieldAlert className="w-4 h-4 text-purple-600" />}
            variant={cappedCount > 0 ? 'warning' : 'default'}
          />
        </div>
      )}

      {/* Filter and Constraint Control Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5 flex-1">
          {/* Search */}
          <div className="relative min-w-[200px]">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search recommendations..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Priority Filter */}
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-xs">
            {['all', 'CRITICAL', 'HIGH', 'MEDIUM', 'HEALTHY'].map(lvl => (
              <button
                key={lvl}
                onClick={() => setPriorityFilter(lvl)}
                className={`px-2 py-1 rounded font-medium capitalize transition-all ${
                  priorityFilter === lvl
                    ? 'bg-white text-slate-900 shadow-xs font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {lvl === 'all' ? 'All' : lvl.toLowerCase()}
              </button>
            ))}
          </div>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={e => setSelectedCategory(e.target.value)}
            className="py-1 px-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none"
          >
            <option value="all">All Categories</option>
            {categories.map(c => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        {/* Budget Allocation Constraint Input */}
        <form onSubmit={handleApplyBudget} className="flex items-center gap-2 text-xs">
          <span className="text-slate-500 font-medium">Budget Cap:</span>
          <div className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 font-semibold">{currencySymbol}</span>
            <input
              type="number"
              min="0"
              placeholder="Unlimited"
              value={budgetCap}
              onChange={e => setBudgetCap(e.target.value)}
              className="w-24 pl-6 pr-2 py-1 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono tabular-nums focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold"
          >
            Apply
          </button>
        </form>
      </div>

      {/* Main Ranked Recommendation Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/75 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-3 text-center w-8">
                  <button
                    onClick={toggleSelectAll}
                    className="text-slate-500 hover:text-blue-600"
                    title="Select/Deselect All Reorder Items"
                  >
                    {plan?.items.filter(i => i.recommended_reorder_qty > 0).length === selectedProductIds.size && selectedProductIds.size > 0 ? (
                      <CheckSquare className="w-4 h-4 text-blue-600" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </th>
                <th className="py-3 px-3">Priority</th>
                <th className="py-3 px-3">Product & SKU</th>
                <th className="py-3 px-3 text-right">Current Stock</th>
                <th className="py-3 px-3 text-right">Daily Demand</th>
                <th className="py-3 px-3 text-right">Lead Time (LTD)</th>
                <th className="py-3 px-3 text-right font-bold text-blue-900">Recommended Qty</th>
                <th className="py-3 px-3 text-center">Shelf-Life Cap</th>
                <th className="py-3 px-3 text-right">Purchase Cost</th>
                <th className="py-3 px-3 text-center">Perishable Risk</th>
                <th className="py-3 px-3">Reason</th>
                <th className="py-3 px-3 text-right">Audit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={12} className="py-12 text-center text-slate-400">
                    Evaluating replenishment math across catalog...
                  </td>
                </tr>
              ) : plan?.items.length === 0 ? (
                <tr>
                  <td colSpan={12} className="py-12 text-center text-slate-500">
                    No recommendations found matching current filters.
                  </td>
                </tr>
              ) : (
                plan?.items.map(item => {
                  const isSelected = selectedProductIds.has(item.product_id);
                  return (
                    <tr
                      key={item.product_id}
                      onClick={() => setSelectedItem(item)}
                      className={`hover:bg-blue-50/40 transition-colors cursor-pointer ${isSelected ? 'bg-blue-50/20' : ''}`}
                    >
                      <td className="py-3 px-3 text-center" onClick={e => e.stopPropagation()}>
                        <button
                          disabled={item.recommended_reorder_qty === 0}
                          onClick={e => toggleSelectOne(item.product_id, e)}
                          className="disabled:opacity-20 text-slate-400 hover:text-blue-600"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-blue-600" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                        </button>
                      </td>
                      <td className="py-3 px-3">
                        <StatusBadge status={item.priority} size="sm" />
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-900">{item.name}</div>
                        <div className="text-[11px] font-mono text-slate-400">
                          {item.sku} • {item.category}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right tabular-nums font-bold">
                        <span className={item.current_stock === 0 ? 'text-red-600' : item.current_stock < 10 ? 'text-amber-600' : 'text-slate-800'}>
                          {item.current_stock}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right tabular-nums text-slate-600">
                        {item.average_daily_demand}/d
                      </td>
                      <td className="py-3 px-3 text-right tabular-nums text-slate-600">
                        {item.lead_time_days}d ({item.lead_time_demand})
                      </td>
                      <td className="py-3 px-3 text-right tabular-nums">
                        {item.recommended_reorder_qty > 0 ? (
                          <span className="font-extrabold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                            {item.recommended_reorder_qty} units
                          </span>
                        ) : (
                          <span className="text-slate-400 font-medium">0</span>
                        )}
                      </td>
                      {/* Shelf-Life Cap Column */}
                      <td className="py-3 px-3 text-center">
                        {item.is_perishable ? (
                          item.shelf_life_capped ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                              Cap: {item.usable_shelf_life ?? 0}d
                            </span>
                          ) : (
                            <span className="text-slate-500 text-[11px]">
                              {item.shelf_life_days}d limit
                            </span>
                          )
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right tabular-nums font-semibold text-slate-900">
                        {item.purchase_cost > 0 ? `${currencySymbol}${item.purchase_cost.toFixed(2)}` : '-'}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {item.is_perishable ? (
                          item.expiry_risk ? (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-100 text-red-800 border border-red-200">
                              Expiry Risk
                            </span>
                          ) : (
                            <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                              Fresh
                            </span>
                          )
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="py-3 px-3 max-w-[200px] text-xs text-slate-600 truncate" title={item.recommendation_reason}>
                        {item.recommendation_reason}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            setSelectedItem(item);
                          }}
                          className="px-2 py-1 text-xs font-semibold rounded bg-slate-100 hover:bg-blue-600 hover:text-white text-slate-700 transition-colors"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="p-3.5 border-t border-slate-200 bg-slate-50/50 flex flex-wrap items-center justify-between text-xs text-slate-500 gap-2">
          <span>
            Ranked by priority score, stockout timeline, supplier MOQ, and perishable shelf-life cap.
          </span>
          <span className="text-[11px] text-slate-400 font-mono">
            Coverage: {plan?.settings.coverage_days}d | Buffer: {plan?.settings.safety_buffer_days}d
          </span>
        </div>
      </div>

      {/* Slide-in Detail Inspection Drawer */}
      <RecommendationDrawer
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        currencySymbol={currencySymbol}
      />
    </div>
  );
};
