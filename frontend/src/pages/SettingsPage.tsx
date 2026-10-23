import React, { useState, useEffect } from 'react';
import { Settings, Save, CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react';
import { api } from '../services/api';
import { SettingsData } from '../types';

interface SettingsPageProps {
  onSettingsUpdated?: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ onSettingsUpdated }) => {
  const [settings, setSettings] = useState<SettingsData>({
    lead_time_days: '7',
    safety_buffer_days: '3',
    coverage_days: '14',
    historical_window_days: '30',
    forecast_horizon_days: '14',
    currency: '$',
    budget: '0.0',
    forecast_method: 'moving_average'
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    api.getSettings()
      .then(res => {
        setSettings(prev => ({ ...prev, ...res }));
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await api.updateSettings(settings);
      setMessage({ type: 'success', text: 'Settings updated successfully! Calculations will now use these new defaults.' });
      if (onSettingsUpdated) onSettingsUpdated();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update settings' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight">System & Replenishment Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Configure default lead times, safety stocks, coverage periods, and planning constraints.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
        {message && (
          <div
            className={`p-4 rounded-lg text-xs flex items-center gap-2 ${
              message.type === 'success'
                ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                : 'bg-red-50 border border-red-200 text-red-800'
            }`}
          >
            {message.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            )}
            <span>{message.text}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Default Supplier Lead Time (Days)</label>
            <input
              type="number"
              min="1"
              value={settings.lead_time_days}
              onChange={e => setSettings({ ...settings, lead_time_days: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-400 mt-1">Fallback lead time when supplier metadata is unspecified.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Default Safety Buffer (Days)</label>
            <input
              type="number"
              min="1"
              value={settings.safety_buffer_days}
              onChange={e => setSettings({ ...settings, safety_buffer_days: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-400 mt-1">Days of buffer stock held against delivery delays.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Target Stock Coverage (Days)</label>
            <input
              type="number"
              min="1"
              value={settings.coverage_days}
              onChange={e => setSettings({ ...settings, coverage_days: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-400 mt-1">Number of days of sales to cover when ordering.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Historical Window (Days)</label>
            <input
              type="number"
              min="7"
              value={settings.historical_window_days}
              onChange={e => setSettings({ ...settings, historical_window_days: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-400 mt-1">Number of past sales days used to compute daily average demand.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Store Currency Symbol</label>
            <select
              value={settings.currency}
              onChange={e => setSettings({ ...settings, currency: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="$">$ (USD)</option>
              <option value="₹">₹ (INR)</option>
              <option value="€">€ (EUR)</option>
              <option value="£">£ (GBP)</option>
            </select>
            <p className="text-[11px] text-slate-400 mt-1">Symbol displayed across financial KPIs and tables.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Default Forecasting Algorithm</label>
            <select
              value={settings.forecast_method}
              onChange={e => setSettings({ ...settings, forecast_method: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="moving_average">Moving Average Baseline (ADD)</option>
              <option value="linear_trend">Linear Trend-Adjusted (Regression)</option>
            </select>
            <p className="text-[11px] text-slate-400 mt-1">Primary method used for reorder projections.</p>
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs font-bold text-slate-700 mb-1">Purchasing Budget Cap ({settings.currency})</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={settings.budget}
              onChange={e => setSettings({ ...settings, budget: e.target.value })}
              placeholder="0.00 for unlimited"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none font-mono"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Set to 0 for unconstrained recommendations. If positive, reorders are capped by priority.
            </p>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-200 flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm shadow-blue-500/20 flex items-center gap-2 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving Settings...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
