import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Users, 
  Activity, 
  Database, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  UserCheck, 
  UserX, 
  Play, 
  Plus, 
  Server
} from 'lucide-react';
import { api } from '../services/api';
import type { User, PipelineRun } from '../types';

export const AdminConsolePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'pipeline' | 'system'>('users');
  const [users, setUsers] = useState<User[]>([]);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // User creation modal
  const [showAddUser, setShowAddUser] = useState(false);
  const [newUser, setNewUser] = useState({ name: '', email: '', password: '', role: 'retailer' });

  // Confirmation dialogs
  const [confirmReset, setConfirmReset] = useState(false);
  const [confirmSeed, setConfirmSeed] = useState(false);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [uData, pData, sData] = await Promise.all([
        api.getAdminUsers(),
        api.getPipelineRuns(15),
        api.getAdminSystem()
      ]);
      setUsers(uData);
      setPipelineRuns(pData.runs || []);
      setSystemHealth(sData);
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.message || 'Failed to load admin telemetry' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleToggleUser = async (userId: number, currentActive: number) => {
    try {
      const nextActive = currentActive === 1 ? 0 : 1;
      await api.updateAdminUser(userId, { active: nextActive });
      setMessage({ type: 'success', text: `User status updated successfully` });
      setTimeout(() => setMessage(null), 3000);
      await fetchAll();
    } catch (err: any) {
      alert(err?.message || 'Failed to update user');
    }
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await api.updateAdminUser(userId, { role: newRole });
      setMessage({ type: 'success', text: `User role updated to ${newRole}` });
      setTimeout(() => setMessage(null), 3000);
      await fetchAll();
    } catch (err: any) {
      alert(err?.message || 'Failed to update role');
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUser.email || !newUser.password || !newUser.name) return;

    try {
      setActionLoading(true);
      await api.createAdminUser(newUser);
      setMessage({ type: 'success', text: `Created user ${newUser.email} (${newUser.role})` });
      setShowAddUser(false);
      setNewUser({ name: '', email: '', password: '', role: 'retailer' });
      await fetchAll();
    } catch (err: any) {
      alert(err?.message || 'Failed to create user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunPipelineNow = async () => {
    try {
      setActionLoading(true);
      const res = await api.runPipeline();
      setMessage({ type: 'success', text: res.message || 'Pipeline triggered successfully' });
      await fetchAll();
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.message || 'Failed to trigger pipeline' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSeedDemoData = async () => {
    try {
      setActionLoading(true);
      setConfirmSeed(false);
      const res = await api.seedDemoData();
      setMessage({ type: 'success', text: res.message || 'Demonstration data re-initialized' });
      await fetchAll();
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.message || 'Failed to seed data' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleResetData = async () => {
    try {
      setActionLoading(true);
      setConfirmReset(false);
      const res = await api.resetDatabase();
      setMessage({ type: 'success', text: res.message || 'Database reset successfully' });
      await fetchAll();
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.message || 'Failed to reset database' });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-7 h-7 text-indigo-600" />
            Admin Console & System Health
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Global governance: user role management, automated pipeline audit logs, and diagnostic controls.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchAll}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button
            onClick={handleRunPipelineNow}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            Run Pipeline Now
          </button>
        </div>
      </div>

      {/* Status Alert Banner */}
      {message && (
        <div
          className={`p-3.5 rounded-lg border text-sm font-medium flex items-center justify-between shadow-xs ${
            message.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          <div className="flex items-center gap-2">
            {message.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            )}
            {message.text}
          </div>
          <button onClick={() => setMessage(null)} className="text-slate-500 hover:text-slate-800">
            &times;
          </button>
        </div>
      )}

      {/* System Health Snapshot Cards */}
      {systemHealth && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Database Status</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-xl font-bold text-emerald-600 font-mono">HEALTHY</span>
              <span className="text-xs text-slate-500 font-mono">{systemHealth.database_size_kb} KB</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">SQLite ACID Storage</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Catalog & Stock</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-slate-900 font-mono">{systemHealth.counts.products}</span>
              <span className="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded-full">Products</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Monitored inventory units</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Sales Ledger</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-slate-900 font-mono">{systemHealth.counts.sales_transactions}</span>
              <span className="text-xs text-purple-600 font-medium bg-purple-50 px-2 py-0.5 rounded-full">Txns</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Historic retail consumption</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Alerts</span>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-amber-600 font-mono">{systemHealth.counts.open_alerts}</span>
              <span className="text-xs text-amber-700 font-medium bg-amber-50 px-2 py-0.5 rounded-full">Open</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Stockout & Expiry events</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('users')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'users'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users className="w-4 h-4" />
          User & Role Governance ({users.length})
        </button>
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'pipeline'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Activity className="w-4 h-4" />
          Pipeline Execution Logs ({pipelineRuns.length})
        </button>
        <button
          onClick={() => setActiveTab('system')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'system'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Database className="w-4 h-4" />
          Demonstration & Data Tools
        </button>
      </div>

      {/* Tab 1: Users Table */}
      {activeTab === 'users' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Registered Platform Stakeholders</h3>
              <p className="text-xs text-slate-500 mt-0.5">Role-based access control with tenant data isolation.</p>
            </div>
            <button
              onClick={() => setShowAddUser(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              Create User
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Role Assignment</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-medium text-slate-900">{u.name}</td>
                    <td className="py-3 px-4 text-slate-600 font-mono">{u.email}</td>
                    <td className="py-3 px-4">
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className="px-2 py-1 border border-slate-200 rounded-md bg-white text-xs font-semibold capitalize text-slate-700"
                      >
                        <option value="retailer">Retailer (Customer)</option>
                        <option value="wholesaler">Wholesaler</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {u.active ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          <UserCheck className="w-3 h-3" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                          <UserX className="w-3 h-3" /> Suspended
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleToggleUser(u.id, u.active ? 1 : 0)}
                        className={`text-xs font-medium px-2.5 py-1 rounded-md transition-colors ${
                          u.active
                            ? 'text-rose-600 hover:bg-rose-50 border border-rose-200'
                            : 'text-emerald-600 hover:bg-emerald-50 border border-emerald-200'
                        }`}
                      >
                        {u.active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Pipeline Execution Runs */}
      {activeTab === 'pipeline' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 bg-slate-50/70 border-b border-slate-200">
            <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-600" />
              Automated Data Pipeline Execution History
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Tracks scheduled runs, watched inbox ingestion (data_inbox/), reorder recalculations, and automated alert evaluations.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Run ID</th>
                  <th className="py-3 px-4">Job Name</th>
                  <th className="py-3 px-4">Triggered By</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Processed Rows</th>
                  <th className="py-3 px-4 text-right">Rejected Rows</th>
                  <th className="py-3 px-4 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {pipelineRuns.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-bold text-slate-800">#{run.id}</td>
                    <td className="py-3 px-4 font-sans font-medium text-slate-900">{run.job_name}</td>
                    <td className="py-3 px-4 font-sans text-slate-500">{run.triggered_by}</td>
                    <td className="py-3 px-4 text-center font-sans">
                      {run.status === 'SUCCESS' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" /> SUCCESS
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                          <AlertTriangle className="w-3 h-3" /> {run.status}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-900">{run.rows_processed}</td>
                    <td className="py-3 px-4 text-right text-rose-600">{run.rows_rejected}</td>
                    <td className="py-3 px-4 text-right font-sans text-slate-500">{run.started_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Demonstration Data Tools */}
      {activeTab === 'system' && (
        <div className="space-y-4">
          <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Server className="w-5 h-5 text-indigo-600" />
              Demonstration Environment Controls
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-2xl">
              Quickly re-populate or clean test datasets for live QUANTIX 2K26 hackathon jury demonstrations.
              All demonstration datasets are deterministic (seeded random number generator).
            </p>

            <div className="mt-6 flex flex-wrap gap-4">
              <button
                onClick={() => setConfirmSeed(true)}
                disabled={actionLoading}
                className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-xs transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className="w-4 h-4" />
                Re-seed Deterministic Demo Data (30 SKUs + 60-Day Sales)
              </button>

              <button
                onClick={() => setConfirmReset(true)}
                disabled={actionLoading}
                className="px-4 py-2.5 bg-white border border-rose-300 text-rose-700 hover:bg-rose-50 font-semibold text-xs rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                Clear All Demonstration Records
              </button>
            </div>
          </div>

          {/* Seed Confirmation Dialog */}
          {confirmSeed && (
            <div className="p-4 bg-indigo-50 border border-indigo-200 rounded-xl text-xs space-y-3">
              <div className="font-bold text-indigo-900">Confirm Demonstration Data Re-seed</div>
              <p className="text-indigo-800">
                This will reset the products, suppliers, 60 days of realistic sales, GST invoice lines, stock expiry batches, and wholesale catalog items.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleSeedDemoData}
                  className="px-3 py-1.5 bg-indigo-600 text-white rounded-md font-semibold"
                >
                  Proceed with Seed
                </button>
                <button
                  onClick={() => setConfirmSeed(false)}
                  className="px-3 py-1.5 bg-white border border-indigo-200 text-indigo-800 rounded-md font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Reset Confirmation Dialog */}
          {confirmReset && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs space-y-3">
              <div className="font-bold text-rose-900">Confirm Database Reset</div>
              <p className="text-rose-800">
                Are you sure? This will truncate all operational tables (products, sales, orders, alerts). This action cannot be undone.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleResetData}
                  className="px-3 py-1.5 bg-rose-600 text-white rounded-md font-semibold"
                >
                  Yes, Reset Everything
                </button>
                <button
                  onClick={() => setConfirmReset(false)}
                  className="px-3 py-1.5 bg-white border border-rose-200 text-rose-800 rounded-md font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create User Modal */}
      {showAddUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full overflow-hidden animate-scale-in">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Plus className="w-4 h-4 text-indigo-600" />
                Register New User
              </h2>
              <button
                onClick={() => setShowAddUser(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Kumar"
                  value={newUser.name}
                  onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. ramesh@store.in"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Initial Password *</label>
                <input
                  type="password"
                  required
                  placeholder="Minimum 6 characters"
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Stakeholder Role *</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white capitalize"
                >
                  <option value="retailer">Retailer (Customer / Store Operator)</option>
                  <option value="wholesaler">Wholesaler (Supplier)</option>
                  <option value="admin">Platform Administrator</option>
                </select>
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddUser(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-semibold shadow-xs disabled:opacity-50"
                >
                  {actionLoading ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
