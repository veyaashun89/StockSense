import React, { useState, useEffect } from 'react';
import {
  Package,
  Plus,
  Upload,
  Download,
  Search,
  Filter,
  Edit2,
  Trash2,
  AlertTriangle,
  X,
  Check,
  Clock,
  Layers
} from 'lucide-react';
import { Product, Supplier } from '../types';
import { api } from '../services/api';
import { DataOverviewStrip } from '../components/overview/DataOverviewStrip';

interface InventoryPageProps {
  currencySymbol?: string;
}

export const InventoryPage: React.FC<InventoryPageProps> = ({ currencySymbol = '$' }) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState<string[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState<Partial<Product>>({
    sku: '',
    name: '',
    category: 'Grocery Staples',
    current_stock: 0,
    unit_cost: 0,
    selling_price: 0,
    lead_time_days: 7,
    is_perishable: 0,
    shelf_life_days: null,
    min_order_qty: 1,
    pack_size: 1,
    safety_buffer_days: 3
  });
  const [formError, setFormError] = useState<string | null>(null);

  // Delete confirm state
  const [deletingProduct, setDeletingProduct] = useState<Product | null>(null);
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null);

  // Load products
  const loadData = async () => {
    setLoading(true);
    try {
      const [prodRes, catRes, supRes] = await Promise.all([
        api.getProducts({
          search,
          category: selectedCategory,
          sort_by: sortBy,
          sort_dir: sortDir,
          page,
          per_page: 50
        }),
        api.getCategories(),
        api.getSuppliers()
      ]);
      setProducts(prodRes.items);
      setTotal(prodRes.total);
      setCategories(catRes);
      setSuppliers(supRes);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [search, selectedCategory, sortBy, sortDir, page]);

  const handleOpenAdd = () => {
    setEditingProduct(null);
    setFormData({
      sku: '',
      name: '',
      category: categories[0] || 'Grocery Staples',
      current_stock: 10,
      unit_cost: 2.5,
      selling_price: 4.99,
      lead_time_days: 7,
      is_perishable: 0,
      shelf_life_days: null,
      min_order_qty: 1,
      pack_size: 1,
      safety_buffer_days: 3
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (p: Product) => {
    setEditingProduct(p);
    setFormData({ ...p });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSaveProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      if (editingProduct) {
        await api.updateProduct(editingProduct.id, formData);
      } else {
        await api.createProduct(formData);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save product');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingProduct) return;
    try {
      const res = await api.deleteProduct(deletingProduct.id);
      setDeleteMessage(res.message);
      setTimeout(() => {
        setDeletingProduct(null);
        setDeleteMessage(null);
        loadData();
      }, 1500);
    } catch (err: any) {
      setDeleteMessage(err.message || 'Failed to delete');
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight">Inventory Management</h1>
          <p className="text-sm text-slate-500 mt-1">
            Maintain product catalog, lead times, perishable shelf lives, and stock positions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href={api.getReportDownloadUrl('inventory')}
            download
            className="px-3.5 py-2 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export CSV</span>
          </a>
          <button
            onClick={handleOpenAdd}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-bold shadow-sm shadow-blue-500/20 hover:bg-blue-700 transition-colors flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Add Product</span>
          </button>
        </div>
      </div>

      {/* Data Ingestion & Active Catalog Strip */}
      <DataOverviewStrip
        lastImport="Production Database (SQLite WAL)"
        rowsRejected={0}
        dateRange="Live Catalog & Movements"
        totalRecords={total}
      />

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by SKU, product name, or category..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
            />
          </div>
          <select
            value={selectedCategory}
            onChange={e => setSelectedCategory(e.target.value)}
            className="py-2 px-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Categories ({categories.length})</option>
            {categories.map(c => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Sort by:</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="py-1.5 px-2 bg-slate-50 border border-slate-200 rounded text-xs text-slate-700 focus:outline-none"
          >
            <option value="name">Product Name</option>
            <option value="sku">SKU</option>
            <option value="current_stock">Current Stock</option>
            <option value="unit_cost">Unit Cost</option>
            <option value="lead_time_days">Lead Time</option>
          </select>
          <button
            onClick={() => setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))}
            className="p-1.5 border border-slate-200 rounded hover:bg-slate-50 text-slate-700"
          >
            {sortDir === 'asc' ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {/* Product Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/75 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">SKU</th>
                <th className="py-3 px-4">Product Name</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 text-right">Current Stock</th>
                <th className="py-3 px-4 text-right">Unit Cost</th>
                <th className="py-3 px-4 text-right">Selling Price</th>
                <th className="py-3 px-4 text-right">Lead Time</th>
                <th className="py-3 px-4 text-center">Perishable / Shelf Life</th>
                <th className="py-3 px-4 text-center">MOQ / Pack</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-400">
                    Loading inventory catalog...
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500">
                    No products found matching your filter criteria.
                  </td>
                </tr>
              ) : (
                products.map(p => (
                  <tr key={p.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900">{p.sku}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900">{p.name}</div>
                      <div className="text-[11px] text-slate-400">{p.supplier_name || 'Direct'}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-600">{p.category}</td>
                    <td className="py-3 px-4 text-right tabular-nums font-bold">
                      <span className={p.current_stock === 0 ? 'text-red-600' : p.current_stock < 10 ? 'text-amber-600' : 'text-slate-900'}>
                        {p.current_stock}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right tabular-nums text-slate-600">
                      {currencySymbol}{p.unit_cost.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right tabular-nums font-medium text-slate-800">
                      {currencySymbol}{p.selling_price.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right tabular-nums text-slate-600">{p.lead_time_days}d</td>
                    <td className="py-3 px-4 text-center">
                      {p.is_perishable ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                          <Clock className="w-3 h-3 text-amber-600" /> {p.shelf_life_days}d shelf life
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs">Non-perishable</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center tabular-nums text-slate-600 text-xs">
                      {p.min_order_qty} / {p.pack_size}pk
                    </td>
                    <td className="py-3 px-4 text-right space-x-1">
                      <button
                        onClick={() => handleOpenEdit(p)}
                        className="p-1 rounded text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                        title="Edit product"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeletingProduct(p)}
                        className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                        title="Delete product"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="p-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
          <span>
            Showing {products.length} of {total} products
          </span>
          <span className="text-[11px] text-slate-400">All inventory positions verified in SQLite</span>
        </div>
      </div>

      {/* Add / Edit Product Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Package className="w-4 h-4 text-blue-600" />
                {editingProduct ? `Edit Product: ${editingProduct.sku}` : 'Add New Inventory Product'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveProduct} className="p-6 space-y-4 overflow-y-auto">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Product SKU *</label>
                  <input
                    type="text"
                    required
                    value={formData.sku || ''}
                    onChange={e => setFormData({ ...formData, sku: e.target.value.toUpperCase() })}
                    placeholder="e.g. SKU-MLK-01"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Product Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.name || ''}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Fresh Whole Milk 1 Gal"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Category *</label>
                  <input
                    type="text"
                    required
                    value={formData.category || ''}
                    onChange={e => setFormData({ ...formData, category: e.target.value })}
                    placeholder="e.g. Dairy & Fresh"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Current Stock Balance *</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={formData.current_stock ?? 0}
                    onChange={e => setFormData({ ...formData, current_stock: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Unit Cost ({currencySymbol}) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={formData.unit_cost ?? 0}
                    onChange={e => setFormData({ ...formData, unit_cost: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Selling Price ({currencySymbol}) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={formData.selling_price ?? 0}
                    onChange={e => setFormData({ ...formData, selling_price: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Supplier Lead Time (Days)</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.lead_time_days ?? 7}
                    onChange={e => setFormData({ ...formData, lead_time_days: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Safety Buffer (Days)</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.safety_buffer_days ?? 3}
                    onChange={e => setFormData({ ...formData, safety_buffer_days: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Supplier MOQ (Units)</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.min_order_qty ?? 1}
                    onChange={e => setFormData({ ...formData, min_order_qty: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Pack Size (Units/Pack)</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.pack_size ?? 1}
                    onChange={e => setFormData({ ...formData, pack_size: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Is Perishable Product?</label>
                  <select
                    value={formData.is_perishable ? 1 : 0}
                    onChange={e => setFormData({ ...formData, is_perishable: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  >
                    <option value={0}>No (Non-perishable shelf item)</option>
                    <option value={1}>Yes (Perishable item with expiry risk)</option>
                  </select>
                </div>
              </div>

              {formData.is_perishable ? (
                <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg space-y-1">
                  <label className="block text-xs font-bold text-amber-900">Perishable Shelf Life (Days) *</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.shelf_life_days ?? ''}
                    onChange={e => setFormData({ ...formData, shelf_life_days: parseInt(e.target.value) || null })}
                    placeholder="e.g. 7 for fresh milk, 14 for yogurt"
                    className="w-full px-3 py-2 border border-amber-300 rounded-lg text-xs tabular-nums focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
                  />
                  <p className="text-[11px] text-amber-800">
                    The reorder engine will strictly cap orders so inventory sells within this window, avoiding spoilage.
                  </p>
                </div>
              ) : null}

              <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm shadow-blue-500/20"
                >
                  {editingProduct ? 'Save Changes' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingProduct && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md p-6 space-y-4">
            <div className="w-12 h-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-bold text-slate-900">Delete Product?</h3>
              <p className="text-xs text-slate-500 mt-1">
                Are you sure you want to delete <span className="font-semibold text-slate-800">{deletingProduct.name}</span> ({deletingProduct.sku})?
              </p>
              <p className="text-[11px] text-slate-400 mt-2">
                If this product has historical sales records, it will be safely archived to preserve financial and forecasting integrity.
              </p>
            </div>
            {deleteMessage && (
              <div className="p-3 bg-slate-100 rounded text-xs text-slate-700 text-center">
                {deleteMessage}
              </div>
            )}
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                disabled={Boolean(deleteMessage)}
                onClick={() => setDeletingProduct(null)}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                disabled={Boolean(deleteMessage)}
                onClick={handleDeleteConfirm}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-sm shadow-red-500/20"
              >
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
