import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Calendar,
  AlertTriangle,
  Info,
  Clock,
  BarChart3,
  CheckCircle2,
  Layers,
  ArrowRight,
  ShieldCheck,
  CalendarDays
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { api } from '../services/api';
import type { ForecastResult, WeeklyForecastResult, Product } from '../types';

interface ForecastPageProps {
  initialProductId?: number | null;
}

export const ForecastPage: React.FC<ForecastPageProps> = ({ initialProductId }) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(initialProductId || null);
  const [granularity, setGranularity] = useState<'daily' | 'weekly'>('daily');
  
  // Daily parameters
  const [horizon, setHorizon] = useState<number>(14);
  const [windowDays, setWindowDays] = useState<number>(30);
  const [method, setMethod] = useState<string>('moving_average');

  // Weekly parameters
  const [horizonWeeks, setHorizonWeeks] = useState<number>(4);

  const [forecast, setForecast] = useState<ForecastResult | null>(null);
  const [weeklyForecast, setWeeklyForecast] = useState<WeeklyForecastResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load product catalog for selector
  useEffect(() => {
    api.getProducts({ per_page: 200 }).then(res => {
      setProducts(res.items);
      if (!selectedProductId && res.items.length > 0) {
        setSelectedProductId(res.items[0].id);
      }
    });
  }, []);

  const runCalculation = async () => {
    if (!selectedProductId) return;
    setLoading(true);
    setError(null);
    try {
      if (granularity === 'daily') {
        const res = await api.getForecast({
          product_id: selectedProductId,
          horizon,
          window: windowDays,
          method
        });
        setForecast(res);
      } else {
        const res = await api.getWeeklyForecast({
          product_id: selectedProductId,
          horizon_weeks: horizonWeeks,
          window: windowDays
        });
        setWeeklyForecast(res);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to calculate demand forecast');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedProductId) {
      runCalculation();
    }
  }, [selectedProductId, granularity, horizon, horizonWeeks, windowDays, method]);

  // Daily Chart Data
  const dailyChartData: any[] = [];
  if (forecast && granularity === 'daily') {
    forecast.historical_series.forEach(item => {
      dailyChartData.push({
        date: item.date,
        actual_sales: item.actual_sales,
        forecast_demand: null
      });
    });

    if (dailyChartData.length > 0) {
      dailyChartData[dailyChartData.length - 1].forecast_demand = dailyChartData[dailyChartData.length - 1].actual_sales;
    }

    forecast.daily_forecast.forEach(item => {
      dailyChartData.push({
        date: item.date,
        actual_sales: null,
        forecast_demand: item.predicted_demand
      });
    });
  }

  // Weekly Chart Data
  const weeklyChartData: any[] = [];
  if (weeklyForecast && granularity === 'weekly') {
    weeklyForecast.historical_weeks.forEach(w => {
      weeklyChartData.push({
        period: `Wk ${w.week_start.slice(5)}`,
        actual_units: w.actual_units,
        predicted_units: null,
        lower_bound: null,
        upper_bound: null
      });
    });

    if (weeklyChartData.length > 0) {
      const last = weeklyChartData[weeklyChartData.length - 1];
      last.predicted_units = last.actual_units;
    }

    weeklyForecast.weekly_forecast.forEach(w => {
      weeklyChartData.push({
        period: `Wk ${w.week_start.slice(5)} (F)`,
        actual_units: null,
        predicted_units: w.predicted_units,
        lower_bound: w.lower_bound,
        upper_bound: w.upper_bound,
        range_label: w.range_label
      });
    });
  }

  const selectedProd = products.find(p => p.id === selectedProductId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight flex items-center gap-2">
            <TrendingUp className="w-7 h-7 text-blue-600" />
            Demand Forecasting Engine
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Empirically project forward demand from historical sales trends, seasonal patterns, and external market signals.
          </p>
        </div>

        {/* Granularity Switcher Pill */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => setGranularity('daily')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              granularity === 'daily'
                ? 'bg-white text-blue-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Daily Horizon
          </button>
          <button
            onClick={() => setGranularity('weekly')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              granularity === 'weekly'
                ? 'bg-white text-blue-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <CalendarDays className="w-3.5 h-3.5" />
            Weekly Predictions (v2)
          </button>
        </div>
      </div>

      {/* Control Panel Card */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-600" /> Model Configuration
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Product</label>
            <select
              value={selectedProductId || ''}
              onChange={e => setSelectedProductId(Number(e.target.value))}
              className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              {products.map(p => (
                <option key={p.id} value={p.id}>
                  {p.sku} — {p.name} ({p.category})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              {granularity === 'daily' ? 'Forecast Horizon (Days)' : 'Forecast Horizon (Weeks)'}
            </label>
            {granularity === 'daily' ? (
              <select
                value={horizon}
                onChange={e => setHorizon(Number(e.target.value))}
                className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value={7}>Next 7 Days (Short-term)</option>
                <option value={14}>Next 14 Days (Standard)</option>
                <option value={30}>Next 30 Days (Monthly Plan)</option>
                <option value={60}>Next 60 Days (Extended)</option>
              </select>
            ) : (
              <select
                value={horizonWeeks}
                onChange={e => setHorizonWeeks(Number(e.target.value))}
                className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value={4}>Next 4 Weeks (1 Month)</option>
                <option value={8}>Next 8 Weeks (2 Months)</option>
                <option value={12}>Next 12 Weeks (Quarterly)</option>
              </select>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Historical Sampling Window</label>
            <select
              value={windowDays}
              onChange={e => setWindowDays(Number(e.target.value))}
              className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value={14}>Past 14 Days</option>
              <option value={30}>Past 30 Days (Recommended)</option>
              <option value={60}>Past 60 Days</option>
              <option value={90}>Past 90 Days</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Forecasting Method</label>
            {granularity === 'daily' ? (
              <select
                value={method}
                onChange={e => setMethod(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value="moving_average">Moving Average Baseline (ADD)</option>
                <option value="linear_trend">Linear Trend-Adjusted (Regression)</option>
              </select>
            ) : (
              <div className="px-3 py-1.5 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-700 font-medium">
                Weekly Moving Average + Residual Bands
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Warning Alert if any */}
      {forecast?.warning && granularity === 'daily' && (
        <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Data Quality Notice:</span> {forecast.warning}
          </div>
        </div>
      )}

      {/* Metric Cards: Daily Mode */}
      {granularity === 'daily' && forecast && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3.5">
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Avg Daily Demand</span>
            <div className="text-2xl font-extrabold text-blue-700 mt-1 tabular-nums">
              {forecast.average_daily_demand} <span className="text-xs font-normal text-slate-400">units/day</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Based on {forecast.window_days}d window</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Lead-Time Demand (LTD)</span>
            <div className="text-2xl font-extrabold text-slate-900 mt-1 tabular-nums">
              {forecast.lead_time_demand} <span className="text-xs font-normal text-slate-400">units</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Expected sales over {forecast.lead_time_days}d lead time</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Trend Slope & Direction</span>
            <div className="text-xl font-bold mt-1 capitalize flex items-center gap-1.5 text-slate-800">
              <TrendingUp className={`w-4 h-4 ${forecast.trend_direction === 'increasing' ? 'text-emerald-600' : forecast.trend_direction === 'decreasing' ? 'text-red-500' : 'text-slate-400'}`} />
              <span>{forecast.trend_direction}</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 font-mono">Slope: {forecast.trend_slope > 0 ? `+${forecast.trend_slope}` : forecast.trend_slope}/day</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Active Sales Days</span>
            <div className="text-2xl font-extrabold text-slate-900 mt-1 tabular-nums">
              {forecast.active_sales_days} <span className="text-xs font-normal text-slate-400">/ {forecast.window_days}d</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">{forecast.total_historical_sold} total units sold</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Model Backtesting</span>
            {forecast.evaluation ? (
              <div>
                <div className="text-lg font-bold text-emerald-700 mt-1 tabular-nums">
                  MAE: {forecast.evaluation.mae} <span className="text-xs font-normal text-slate-500">| RMSE: {forecast.evaluation.rmse}</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Tested on held-out 7-day period</p>
              </div>
            ) : (
              <div>
                <div className="text-sm font-semibold text-slate-400 mt-2">N/A</div>
                <p className="text-[11px] text-slate-400 mt-1">Requires ≥21 days history</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Metric Cards: Weekly Mode */}
      {granularity === 'weekly' && weeklyForecast && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Avg Weekly Run-Rate</span>
            <div className="text-2xl font-extrabold text-blue-700 mt-1 tabular-nums">
              {weeklyForecast.avg_weekly_demand} <span className="text-xs font-normal text-slate-400">units/week</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Aggregated across {weeklyForecast.historical_weeks_count} ISO weeks</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Predicted {horizonWeeks}-Week Volume</span>
            <div className="text-2xl font-extrabold text-emerald-700 mt-1 tabular-nums">
              {weeklyForecast.weekly_forecast.reduce((a, b) => a + b.predicted_units, 0)} <span className="text-xs font-normal text-slate-400">units</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Total projected customer consumption</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Market Data Adjustment</span>
            <div className="text-xl font-bold mt-1 text-slate-800 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>
                {weeklyForecast.market_adjustment ? `${(weeklyForecast.market_adjustment.multiplier * 100).toFixed(0)}%` : '100% (Unadjusted)'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              {weeklyForecast.market_adjustment?.reasons?.[0] || 'Base unadjusted trend'}
            </p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Forecast Horizon Span</span>
            <div className="text-2xl font-extrabold text-slate-900 mt-1 tabular-nums">
              {horizonWeeks} Weeks
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Feed into reorder planner for long lead times</p>
          </div>
        </div>
      )}

      {/* Main Chart */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              {selectedProd?.name || 'Product'} Demand Trajectory ({granularity.toUpperCase()})
            </h2>
            <p className="text-xs text-slate-500">
              {granularity === 'daily'
                ? 'Observed daily sales (bars) vs. Predicted forward demand curve (green dashed line)'
                : 'ISO Weekly aggregated sales (bars) vs. Weekly bucket predictions with uncertainty interval'}
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-slate-600">
              <span className="w-3 h-3 rounded-sm bg-blue-500 inline-block" /> Historical
            </span>
            <span className="flex items-center gap-1.5 text-slate-600">
              <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> Forecast
            </span>
          </div>
        </div>

        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            {granularity === 'daily' ? (
              <ComposedChart data={dailyChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis
                  dataKey="date"
                  tickFormatter={d => {
                    const parts = d.split('-');
                    return `${parts[1]}/${parts[2]}`;
                  }}
                  tick={{ fontSize: 11, fill: '#64748B' }}
                />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-slate-900 text-white p-3 rounded-lg text-xs shadow-lg space-y-1">
                          <p className="font-semibold text-slate-300">{label}</p>
                          {payload.map((p: any, idx: number) => {
                            if (p.value === null || p.value === undefined) return null;
                            return (
                              <p key={idx} style={{ color: p.color }}>
                                {p.name === 'actual_sales' ? 'Historical Sales' : 'Forecast Demand'}:{' '}
                                <span className="font-bold">{p.value} units</span>
                              </p>
                            );
                          })}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="actual_sales" name="actual_sales" fill="#3B82F6" radius={[4, 4, 0, 0]} maxBarSize={30} />
                <Line
                  type="monotone"
                  dataKey="forecast_demand"
                  name="forecast_demand"
                  stroke="#10B981"
                  strokeWidth={3}
                  strokeDasharray="4 4"
                  dot={{ r: 3, fill: '#10B981' }}
                />
              </ComposedChart>
            ) : (
              <ComposedChart data={weeklyChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#64748B' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-slate-900 text-white p-3 rounded-lg text-xs shadow-lg space-y-1">
                          <p className="font-semibold text-slate-300">{label}</p>
                          {payload.map((p: any, idx: number) => {
                            if (p.value === null || p.value === undefined) return null;
                            return (
                              <p key={idx} style={{ color: p.color }}>
                                {p.name === 'actual_units' ? 'Actual Sold' : 'Predicted Demand'}:{' '}
                                <span className="font-bold">{p.value} units</span>
                              </p>
                            );
                          })}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="actual_units" name="actual_units" fill="#3B82F6" radius={[4, 4, 0, 0]} maxBarSize={35} />
                <Line
                  type="monotone"
                  dataKey="predicted_units"
                  name="predicted_units"
                  stroke="#10B981"
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#10B981' }}
                />
              </ComposedChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>

      {/* Weekly Breakdown Table (when Weekly mode active) */}
      {granularity === 'weekly' && weeklyForecast && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 bg-slate-50/70 border-b border-slate-200">
            <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Weekly Prediction Buckets & Uncertainty Bounds
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Residual-based estimate range (not a guarantee). Helps retailers anticipate supplier order cadence.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-4">Week Sequence</th>
                  <th className="py-2.5 px-4">Week Start Date</th>
                  <th className="py-2.5 px-4 text-right">Lower Bound</th>
                  <th className="py-2.5 px-4 text-right font-bold text-emerald-800">Predicted Demand</th>
                  <th className="py-2.5 px-4 text-right">Upper Bound</th>
                  <th className="py-2.5 px-4 text-center">Estimate Range</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {weeklyForecast.weekly_forecast.map((w) => (
                  <tr key={w.week_number} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-4 font-sans font-medium text-slate-800">Week +{w.week_number}</td>
                    <td className="py-2.5 px-4 text-slate-600 font-sans">{w.week_start}</td>
                    <td className="py-2.5 px-4 text-right text-slate-500">{w.lower_bound} units</td>
                    <td className="py-2.5 px-4 text-right font-bold text-emerald-600 text-sm">{w.predicted_units} units</td>
                    <td className="py-2.5 px-4 text-right text-slate-500">{w.upper_bound} units</td>
                    <td className="py-2.5 px-4 text-center font-sans">
                      <span className="px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-700 border border-slate-200">
                        {w.range_label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
