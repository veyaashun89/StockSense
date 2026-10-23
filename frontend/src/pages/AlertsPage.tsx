import React, { useState, useEffect } from 'react';
import {
  Bell,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  RefreshCw,
  Filter,
  Check,
  ShieldCheck,
  Clock
} from 'lucide-react';
import { api } from '../services/api';
import { AlertItem } from '../types';

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [total, setTotal] = useState(0);
  const [openCount, setOpenCount] = useState(0);
  const [criticalCount, setCriticalCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const [statusFilter, setStatusFilter] = useState('OPEN');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const res = await api.getAlerts({
        status: statusFilter,
        severity: severityFilter
      });
      setAlerts(res.items);
      setTotal(res.total);
      setOpenCount(res.open_count);
      setCriticalCount(res.critical_count);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [statusFilter, severityFilter]);

  const handleStatusChange = async (alertId: number, newStatus: 'ACKNOWLEDGED' | 'RESOLVED') => {
    try {
      await api.patchAlert(alertId, newStatus);
      loadAlerts();
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleEvaluateRules = async () => {
    setIsEvaluating(true);
    setActionMessage(null);
    try {
      const res = await api.evaluateAlerts();
      setActionMessage(res.message);
      loadAlerts();
    } catch (err: any) {
      setActionMessage(err.message || 'Evaluation failed');
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-red-100 text-red-800">
              Automated Surveillance
            </span>
            <span className="text-xs text-slate-400">• Rule-Based Deduplication</span>
          </div>
          <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight">Automated Exception Alerts</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time notifications for imminent stockouts, buffer breaches, overstock, and perishable expiration risks.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleEvaluateRules}
            disabled={isEvaluating}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm shadow-blue-500/20 flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isEvaluating ? 'animate-spin' : ''}`} />
            <span>{isEvaluating ? 'Evaluating Rules...' : 'Re-Evaluate Alert Rules'}</span>
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Summary KPI Badges */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Open Alerts</span>
            <div className="text-2xl font-extrabold text-slate-900 mt-0.5 tabular-nums">{openCount}</div>
            <p className="text-[11px] text-slate-400 mt-1">Requiring retailer attention</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <Bell className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-red-200 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-red-700 uppercase tracking-wider">Critical Stockouts</span>
            <div className="text-2xl font-extrabold text-red-600 mt-0.5 tabular-nums">{criticalCount}</div>
            <p className="text-[11px] text-red-500 mt-1">Depletes prior to supplier arrival</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-red-50 text-red-600 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Deduplication Engine</span>
            <div className="text-base font-bold text-emerald-700 mt-0.5 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" /> Auto-Resolving
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Clears alerts automatically when stock recovers</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter Tabs Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500">Status:</span>
          {['OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'all'].map(st => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
                statusFilter === st
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-50 border border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              {st === 'all' ? 'All Alerts' : st.toLowerCase()}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500">Severity:</span>
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 focus:outline-none"
          >
            <option value="all">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="INFO">Info</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {loading ? (
          <div className="bg-white p-12 text-center text-xs text-slate-400 rounded-xl border border-slate-200">
            Checking rule conditions...
          </div>
        ) : alerts.length === 0 ? (
          <div className="bg-white p-12 text-center rounded-xl border border-slate-200 space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
            <h3 className="text-sm font-bold text-slate-800">No Alerts Matching Filters</h3>
            <p className="text-xs text-slate-400">All inventory positions, forecasts, and supply lines are healthy.</p>
          </div>
        ) : (
          alerts.map(a => {
            const isCrit = a.severity === 'CRITICAL';
            const isHigh = a.severity === 'HIGH';
            const borderCol = isCrit ? 'border-red-200 bg-red-50/20' : isHigh ? 'border-amber-200 bg-amber-50/20' : 'border-slate-200 bg-white';
            const badgeBg = isCrit ? 'bg-red-100 text-red-800' : isHigh ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800';

            return (
              <div
                key={a.id}
                className={`p-5 rounded-xl border ${borderCol} shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all`}
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${badgeBg}`}>
                      {a.severity}
                    </span>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                      {a.alert_type.replace(/_/g, ' ')}
                    </span>
                    {a.sku && (
                      <span className="text-xs font-mono font-bold text-slate-900 bg-slate-200/60 px-1.5 py-0.5 rounded">
                        {a.sku}
                      </span>
                    )}
                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {new Date(a.created_at).toLocaleString()}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{a.title}</h3>
                  <p className="text-xs text-slate-700">{a.message}</p>
                  {a.explanation && (
                    <p className="text-[11px] text-slate-500 bg-slate-50 p-2 rounded border border-slate-100">
                      <span className="font-semibold text-slate-600">Explanation:</span> {a.explanation}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {a.status === 'OPEN' && (
                    <>
                      <button
                        onClick={() => handleStatusChange(a.id, 'ACKNOWLEDGED')}
                        className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
                      >
                        Acknowledge
                      </button>
                      <button
                        onClick={() => handleStatusChange(a.id, 'RESOLVED')}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors flex items-center gap-1"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Resolve</span>
                      </button>
                    </>
                  )}
                  {a.status === 'ACKNOWLEDGED' && (
                    <>
                      <span className="text-[11px] font-medium text-slate-400 mr-2">Acknowledged</span>
                      <button
                        onClick={() => handleStatusChange(a.id, 'RESOLVED')}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors flex items-center gap-1"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Resolve</span>
                      </button>
                    </>
                  )}
                  {a.status === 'RESOLVED' && (
                    <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
