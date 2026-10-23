import React from 'react';
import { X, AlertTriangle, Clock, ShieldCheck, Box, DollarSign, Calendar, Info, Layers } from 'lucide-react';
import { ReorderItem } from '../../types';
import { StatusBadge } from './StatusBadge';

interface RecommendationDrawerProps {
  item: ReorderItem | null;
  onClose: () => void;
  currencySymbol?: string;
}

export const RecommendationDrawer: React.FC<RecommendationDrawerProps> = ({
  item,
  onClose,
  currencySymbol = '$'
}) => {
  if (!item) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 overflow-y-auto">
        {/* Drawer Header */}
        <div className="p-6 border-b border-slate-200 flex items-start justify-between bg-slate-50/60 sticky top-0 z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-200 text-slate-800">
                {item.sku}
              </span>
              <span className="text-xs font-medium text-slate-500">{item.category}</span>
              <StatusBadge status={item.priority} size="sm" />
              {item.expiry_risk && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-red-100 text-red-800">
                  <AlertTriangle className="w-3 h-3" /> Expiry Risk
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold text-slate-900">{item.name}</h2>
            <p className="text-xs text-slate-500 mt-0.5">Supplier: {item.supplier_name}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="p-6 space-y-6">
          {/* Top Recommendation Banner */}
          <div className="bg-blue-50/70 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-700">Recommended Order</span>
              <div className="text-3xl font-extrabold text-blue-900 mt-0.5 tabular-nums">
                {item.recommended_reorder_qty} <span className="text-sm font-medium text-blue-700">units</span>
              </div>
              <p className="text-xs text-blue-600 mt-1">
                Estimated Cost: {currencySymbol}{item.purchase_cost.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </p>
            </div>
            <div className="text-right">
              <span className="text-xs font-medium text-slate-500">Days to Stockout</span>
              <div className={`text-2xl font-bold tabular-nums ${item.days_until_stockout <= item.lead_time_days ? 'text-red-600' : 'text-slate-800'}`}>
                {item.days_until_stockout >= 999 ? '90+' : `${item.days_until_stockout}d`}
              </div>
              <span className="text-xs text-slate-500">Lead time: {item.lead_time_days}d</span>
            </div>
          </div>

          {/* Key Parameters Matrix */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-slate-400" /> Inventory & Supplier Parameters
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                <span className="text-xs text-slate-500">Current Stock</span>
                <p className="text-base font-bold text-slate-900 tabular-nums">{item.current_stock} units</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                <span className="text-xs text-slate-500">Avg Daily Demand</span>
                <p className="text-base font-bold text-slate-900 tabular-nums">{item.average_daily_demand}/day</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                <span className="text-xs text-slate-500">Supplier Lead Time</span>
                <p className="text-base font-bold text-slate-900 tabular-nums">{item.lead_time_days} days</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                <span className="text-xs text-slate-500">Safety Buffer</span>
                <p className="text-base font-bold text-slate-900 tabular-nums">{item.safety_buffer_days} days</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                <span className="text-xs text-slate-500">Pack Size</span>
                <p className="text-base font-bold text-slate-900 tabular-nums">{item.pack_size} units/pack</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                <span className="text-xs text-slate-500">Minimum Order (MOQ)</span>
                <p className="text-base font-bold text-slate-900 tabular-nums">{item.min_order_qty} units</p>
              </div>
            </div>
          </div>

          {/* Mathematical Step-by-Step Traceability */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
              <Info className="w-4 h-4 text-slate-400" /> Replenishment Formula Trace
            </h3>
            <div className="space-y-2.5 text-xs text-slate-700">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between items-center font-semibold text-slate-800">
                  <span>1. Lead-Time Demand (LTD)</span>
                  <span className="tabular-nums font-bold">{item.lead_time_demand} units</span>
                </div>
                <p className="text-slate-500 font-mono text-[11px]">
                  ADD ({item.average_daily_demand}) × Lead Time ({item.lead_time_days}d)
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between items-center font-semibold text-slate-800">
                  <span>2. Safety Stock (SS)</span>
                  <span className="tabular-nums font-bold">{item.safety_stock} units</span>
                </div>
                <p className="text-slate-500 font-mono text-[11px]">
                  ADD ({item.average_daily_demand}) × Safety Buffer ({item.safety_buffer_days}d)
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between items-center font-semibold text-slate-800">
                  <span>3. Reorder Point (ROP)</span>
                  <span className="tabular-nums font-bold text-blue-700">{item.reorder_point} units</span>
                </div>
                <p className="text-slate-500 font-mono text-[11px]">
                  LTD ({item.lead_time_demand}) + SS ({item.safety_stock}) = {item.reorder_point}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between items-center font-semibold text-slate-800">
                  <span>4. Target Stock Level</span>
                  <span className="tabular-nums font-bold">{item.target_stock} units</span>
                </div>
                <p className="text-slate-500 font-mono text-[11px]">
                  ADD × ({item.lead_time_days}d lead + {item.calculation_trace.coverage_days}d coverage) + SS = {item.target_stock}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between items-center font-semibold text-slate-800">
                  <span>5. Base Deficit Quantity</span>
                  <span className="tabular-nums font-bold">{item.base_quantity} units</span>
                </div>
                <p className="text-slate-500 font-mono text-[11px]">
                  max(0, Target Stock ({item.target_stock}) - Current Stock ({item.current_stock}))
                </p>
              </div>

              {/* Shelf Life Constraints */}
              {item.is_perishable && (
                <div className={`p-3 rounded-lg border space-y-1.5 ${item.shelf_life_capped ? 'bg-amber-50/70 border-amber-200' : 'bg-slate-50 border-slate-200'}`}>
                  <div className="flex justify-between items-center font-semibold text-slate-800">
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-amber-600" /> 6. Perishable Shelf-Life Cap
                    </span>
                    <span className="tabular-nums font-bold">
                      {item.shelf_life_days}d shelf life
                    </span>
                  </div>
                  <p className="text-slate-600 text-xs">
                    Usable selling window: {item.usable_shelf_life ?? 'N/A'} days after delivery.
                  </p>
                  {item.shelf_life_note && (
                    <p className="text-amber-800 font-medium text-xs bg-amber-100/70 p-2 rounded">
                      {item.shelf_life_note}
                    </p>
                  )}
                </div>
              )}

              {/* Pack Size & MOQ Adjustments */}
              {(item.pack_rounding_applied || item.moq_applied) && (
                <div className="p-3 rounded-lg bg-blue-50/40 border border-blue-200 space-y-1.5">
                  <div className="flex justify-between items-center font-semibold text-blue-900">
                    <span className="flex items-center gap-1.5">
                      <Box className="w-3.5 h-3.5 text-blue-600" /> 7. Supplier Packaging Adjustments
                    </span>
                    <span className="tabular-nums font-bold">{item.recommended_reorder_qty} units</span>
                  </div>
                  <ul className="list-disc list-inside text-blue-800 space-y-0.5 text-xs">
                    {item.pack_rounding_applied && (
                      <li>Rounded up to pack size of {item.pack_size} units</li>
                    )}
                    {item.moq_applied && (
                      <li>Enforced supplier Minimum Order Quantity (MOQ) of {item.min_order_qty} units</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Decision Signals and Reasons */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-slate-400" /> Evaluation Signals
            </h3>
            <div className="space-y-2">
              {item.signals.map((sig, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
                    sig.severity === 'critical'
                      ? 'bg-red-50/80 border-red-200 text-red-900'
                      : sig.severity === 'high'
                      ? 'bg-amber-50/80 border-amber-200 text-amber-900'
                      : 'bg-slate-50 border-slate-200 text-slate-800'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full mt-1 shrink-0 ${
                    sig.severity === 'critical' ? 'bg-red-600' : sig.severity === 'high' ? 'bg-amber-600' : 'bg-blue-600'
                  }`} />
                  <div>
                    <span className="font-semibold">{sig.type.replace(/_/g, ' ')}:</span>{' '}
                    <span>{sig.message}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 mt-auto flex items-center justify-between sticky bottom-0">
          <div className="text-xs text-slate-500">
            Calculated via StockSense Planning Engine
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 text-white text-xs font-semibold hover:bg-slate-900 transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};
