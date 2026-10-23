import React, { useState, useEffect } from 'react';
import {
  Database,
  Sparkles,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileText,
  RefreshCw,
  HardDrive,
  Calendar,
  Layers
} from 'lucide-react';
import { api } from '../services/api';
import { DataStatus } from '../types';
import { DataOverviewStrip } from '../components/overview/DataOverviewStrip';

interface DataManagementPageProps {
  onDataChanged?: () => void;
}

export const DataManagementPage: React.FC<DataManagementPageProps> = ({ onDataChanged }) => {
  const [status, setStatus] = useState<DataStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await api.getDataStatus();
      setStatus(res);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleSeedData = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      const res = await api.seedDemoData();
      setMessage({ type: 'success', text: res.message });
      loadStatus();
      if (onDataChanged) onDataChanged();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to seed sample data' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleResetData = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      const res = await api.resetDatabase();
      setMessage({ type: 'success', text: res.message });
      setShowResetConfirm(false);
      loadStatus();
      if (onDataChanged) onDataChanged();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to reset database' });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight">Data Management & Diagnostics</h1>
        <p className="text-sm text-slate-500 mt-1">
          Monitor database health, inspect import batches, and manage sample datasets for hackathon evaluation.
        </p>
      </div>

      {/* Past Records and Import Ingestion Overview Strip */}
      <DataOverviewStrip
        lastImport="Excel / CSV Pipeline Batch"
        rowsRejected={0}
        dateRange="Rolling 30 Days (Sales & Movements)"
        totalRecords={status?.total_sales_records ?? 0}
      />

      {message && (
        <div
          className={`p-4 rounded-xl text-xs flex items-center gap-2 ${
            message.type === 'success'
              ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Database Diagnostics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium">Active Products</span>
          <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">
            {status?.active_products ?? 0}
          </div>
          <span className="text-[11px] text-slate-400">Indexed in catalog</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium">Suppliers Registered</span>
          <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">
            {status?.total_suppliers ?? 0}
          </div>
          <span className="text-[11px] text-slate-400">With lead-time terms</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium">Sales Records</span>
          <div className="text-2xl font-bold text-blue-700 mt-1 tabular-nums">
            {status?.total_sales_records ?? 0}
          </div>
          <span className="text-[11px] text-slate-400">Historical transactions</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium">Database Storage</span>
          <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">
            {status?.database_size_kb ?? 0} KB
          </div>
          <span className="text-[11px] text-slate-400">SQLite WAL mode</span>
        </div>
      </div>

      {/* Demonstration Dataset Operations */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600" /> Hackathon Demonstration Dataset Initializer
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Seeds 24 realistic products (staples, dairy with perishability constraints, bakery, packaged goods, beverages, household essentials) and 60 days of deterministic daily transactions.
            </p>
          </div>
          <button
            onClick={handleSeedData}
            disabled={actionLoading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm shadow-blue-500/20 flex items-center gap-2 shrink-0 disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{actionLoading ? 'Seeding...' : 'Load Demo Data'}</span>
          </button>
        </div>
      </div>

      {/* Danger Zone: Reset Database */}
      <div className="bg-red-50/40 rounded-xl border border-red-200 p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-bold text-red-900 flex items-center gap-2">
              <Trash2 className="w-4 h-4 text-red-600" /> Reset Database
            </h2>
            <p className="text-xs text-red-700 mt-1">
              Wipes all products, sales records, suppliers, and import batches to test initial onboarding states.
            </p>
          </div>
          <button
            onClick={() => setShowResetConfirm(true)}
            disabled={actionLoading}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-sm shadow-red-500/20 flex items-center gap-2 shrink-0 disabled:opacity-50"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Reset All Tables</span>
          </button>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md p-6 space-y-4">
            <div className="w-12 h-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-bold text-slate-900">Confirm Complete Database Reset</h3>
              <p className="text-xs text-slate-500 mt-1">
                This action will delete all products, sales records, and audit logs. This cannot be undone.
              </p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={() => setShowResetConfirm(false)}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleResetData}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold"
              >
                {actionLoading ? 'Resetting...' : 'Yes, Delete Everything'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
