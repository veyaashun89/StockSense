import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  TrendingUp, 
  Plus, 
  Store, 
  ShieldCheck, 
  Calendar, 
  Clock, 
  AlertCircle,
  Package,
  CheckCircle2
} from 'lucide-react';
import { api } from '../services/api';
import type { WholesaleCatalogItem } from '../types';

export const WholesaleCatalogPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'catalog' | 'signals'>('catalog');
  const [catalogItems, setCatalogItems] = useState<WholesaleCatalogItem[]>([]);
  const [demandSignals, setDemandSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [form, setForm] = useState({
    sku: '',
    name: '',
    category: 'Packaged Foods',
    wholesale_price: 100,
    moq: 10,
    pack_size: 5,
    lead_time_days: 3,
    shelf_life_days: '',
    available_stock: 500
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [catData, signalsData] = await Promise.all([
        api.getWholesaleCatalog(),
        api.getWholesaleDemandSignals()
      ]);
      setCatalogItems(catData);
      setDemandSignals(signalsData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load wholesale data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.sku || !form.name) return;

    try {
      setSubmitting(true);
      await api.addWholesaleCatalogItem({
        sku: form.sku.trim().toUpperCase(),
        name: form.name.trim(),
        category: form.category,
        wholesale_price: Number(form.wholesale_price),
        moq: Number(form.moq),
        pack_size: Number(form.pack_size),
        lead_time_days: Number(form.lead_time_days),
        shelf_life_days: form.shelf_life_days ? Number(form.shelf_life_days) : null,
        available_stock: Number(form.available_stock)
      });
      setSuccessMsg(`Product ${form.name} added to wholesale catalog!`);
      setTimeout(() => setSuccessMsg(null), 4000);
      setShowAddModal(false);
      setForm({
        sku: '',
        name: '',
        category: 'Packaged Foods',
        wholesale_price: 100,
        moq: 10,
        pack_size: 5,
        lead_time_days: 3,
        shelf_life_days: '',
        available_stock: 500
      });
      await fetchData();
    } catch (err: any) {
      alert(err?.message || 'Failed to add item');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Layers className="w-7 h-7 text-blue-600" />
            Wholesale Catalog & Signals
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage wholesale inventory specifications, supplier lead times, and view anonymized retail demand projections.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Wholesale SKU
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {successMsg && (
        <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            {successMsg}
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-700 hover:text-emerald-900">
            &times;
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Catalog SKUs</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-slate-900">{catalogItems.length}</span>
            <span className="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded-full">Active</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Available for retailer reordering</p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Wholesale Stock</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-emerald-600 font-mono">
              {catalogItems.reduce((acc, it) => acc + (it.available_stock || 0), 0).toLocaleString()}
            </span>
            <span className="text-xs text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded-full">Units</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Warehouse ready for dispatch</p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Anonymized Stores Monitored</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-slate-900">{demandSignals.length} SKUs</span>
            <span className="text-xs text-purple-600 font-medium bg-purple-50 px-2 py-0.5 rounded-full">Shared Signals</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Aggregate retail consumption rate</p>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('catalog')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'catalog'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Package className="w-4 h-4" />
          Wholesale Catalog ({catalogItems.length})
        </button>
        <button
          onClick={() => setActiveTab('signals')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'signals'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Upstream Demand Projections ({demandSignals.length})
        </button>
      </div>

      {/* Tab 1: Wholesale Catalog */}
      {activeTab === 'catalog' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-slate-500">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3" />
              <p className="text-sm">Loading wholesale catalog...</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center text-rose-600">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
              <p className="text-sm font-medium">{error}</p>
            </div>
          ) : catalogItems.length === 0 ? (
            <div className="p-12 text-center text-slate-400">
              <Package className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p className="text-base font-semibold text-slate-700">Catalog is empty</p>
              <p className="text-xs text-slate-500 mt-1">Add your first wholesale SKU to allow retail stores to raise orders.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-4">SKU</th>
                    <th className="py-3 px-4">Product Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4 text-right">Wholesale Price</th>
                    <th className="py-3 px-4 text-right">MOQ</th>
                    <th className="py-3 px-4 text-right">Pack Size</th>
                    <th className="py-3 px-4 text-center">Lead Time</th>
                    <th className="py-3 px-4 text-center">Shelf Life</th>
                    <th className="py-3 px-4 text-right">Available Stock</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {catalogItems.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-4 font-bold text-blue-600">{item.sku}</td>
                      <td className="py-3 px-4 font-sans font-medium text-slate-900">{item.name}</td>
                      <td className="py-3 px-4 font-sans text-slate-500">
                        <span className="px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-700">
                          {item.category}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-slate-900">₹{item.wholesale_price.toFixed(2)}</td>
                      <td className="py-3 px-4 text-right text-slate-700">{item.moq} units</td>
                      <td className="py-3 px-4 text-right text-slate-700">{item.pack_size} units</td>
                      <td className="py-3 px-4 text-center text-slate-700">
                        <span className="inline-flex items-center gap-1 font-sans text-xs">
                          <Clock className="w-3 h-3 text-slate-400" />
                          {item.lead_time_days} days
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center text-slate-700 font-sans">
                        {item.shelf_life_days ? (
                          <span className="px-2 py-0.5 rounded-md text-xs bg-amber-50 text-amber-800 border border-amber-200">
                            {item.shelf_life_days} days
                          </span>
                        ) : (
                          <span className="text-slate-400 text-xs">Non-perishable</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-emerald-600">
                        {item.available_stock.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Upstream Demand Signals */}
      {activeTab === 'signals' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 bg-slate-50/70 border-b border-slate-200">
            <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              Aggregated Retail Demand Signals (Anonymized)
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Derived from connected retail shops. Wholesalers can forecast supplier re-stocking volumes before purchase orders are officially raised.
            </p>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-500">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3" />
              <p className="text-sm">Aggregating demand signals...</p>
            </div>
          ) : demandSignals.length === 0 ? (
            <div className="p-12 text-center text-slate-400">
              <Store className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p className="text-base font-semibold text-slate-700">No demand signals available</p>
              <p className="text-xs text-slate-500 mt-1">Connect retail stores with sales data to populate upstream demand.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-4">SKU</th>
                    <th className="py-3 px-4">Product Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4 text-right">Avg Daily Retail Demand</th>
                    <th className="py-3 px-4 text-right">Projected 7-Day Demand</th>
                    <th className="py-3 px-4 text-center">Privacy & Sharing</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {demandSignals.map((sig, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-4 font-bold text-blue-600">{sig.sku}</td>
                      <td className="py-3 px-4 font-sans font-medium text-slate-900">{sig.product_name}</td>
                      <td className="py-3 px-4 font-sans text-slate-500">
                        <span className="px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-700">
                          {sig.category}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-slate-700 font-bold">
                        {sig.avg_daily_store_demand} units/day
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-blue-600">
                        {sig.projected_weekly_demand} units/week
                      </td>
                      <td className="py-3 px-4 text-center font-sans">
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          <ShieldCheck className="w-3 h-3" /> Anonymized
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Add Wholesale SKU Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full overflow-hidden animate-scale-in">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Plus className="w-4 h-4 text-blue-600" />
                Add Wholesale Catalog SKU
              </h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleAddSubmit} className="p-6 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">SKU *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. BEV-001"
                    value={form.sku}
                    onChange={e => setForm({ ...form, sku: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg uppercase font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Product Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Filter Coffee 200g"
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Category</label>
                  <select
                    value={form.category}
                    onChange={e => setForm({ ...form, category: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white"
                  >
                    <option value="Dairy & Bakery">Dairy & Bakery</option>
                    <option value="Staples & Grains">Staples & Grains</option>
                    <option value="Packaged Foods">Packaged Foods</option>
                    <option value="Personal Care">Personal Care</option>
                    <option value="Household Essentials">Household Essentials</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Wholesale Price (₹) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={form.wholesale_price}
                    onChange={e => setForm({ ...form, wholesale_price: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">MOQ (Units)</label>
                  <input
                    type="number"
                    min="1"
                    value={form.moq}
                    onChange={e => setForm({ ...form, moq: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Pack Size</label>
                  <input
                    type="number"
                    min="1"
                    value={form.pack_size}
                    onChange={e => setForm({ ...form, pack_size: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Lead Time (Days)</label>
                  <input
                    type="number"
                    min="1"
                    value={form.lead_time_days}
                    onChange={e => setForm({ ...form, lead_time_days: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Shelf Life (Days, Optional)</label>
                  <input
                    type="number"
                    placeholder="e.g. 7 (Perishable)"
                    value={form.shelf_life_days}
                    onChange={e => setForm({ ...form, shelf_life_days: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Available Wholesale Stock</label>
                  <input
                    type="number"
                    min="0"
                    value={form.available_stock}
                    onChange={e => setForm({ ...form, available_stock: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold shadow-xs disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : 'Add Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
