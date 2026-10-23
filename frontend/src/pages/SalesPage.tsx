import React, { useState, useEffect } from 'react';
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  FileText,
  Search,
  Filter,
  Download,
  Calendar,
  AlertTriangle,
  Layers,
  ArrowRight,
  Database,
  Receipt,
  Boxes,
  TrendingUp,
  Clock,
  ShieldCheck,
  Plus
} from 'lucide-react';
import { api } from '../services/api';
import type { CsvValidationResponse, GstLine, StockBatch, MarketSignal } from '../types';

interface SalesPageProps {
  currencySymbol?: string;
}

export const SalesPage: React.FC<SalesPageProps> = ({ currencySymbol = '₹' }) => {
  const [topTab, setTopTab] = useState<'sales' | 'gst' | 'stock' | 'market'>('sales');

  // --- 1. Direct Sales State ---
  const [sales, setSales] = useState<any[]>([]);
  const [salesTotal, setSalesTotal] = useState(0);
  const [salesLoading, setSalesLoading] = useState(true);
  const [salesPage, setSalesPage] = useState(1);
  const [salesSkuFilter, setSalesSkuFilter] = useState('');
  const [salesFile, setSalesFile] = useState<File | null>(null);
  const [salesValidation, setSalesValidation] = useState<CsvValidationResponse | null>(null);
  const [salesCommitting, setSalesCommitting] = useState(false);
  const [salesMsg, setSalesMsg] = useState<string | null>(null);

  // --- 2. GST State ---
  const [gstLines, setGstLines] = useState<GstLine[]>([]);
  const [gstLoading, setGstLoading] = useState(false);
  const [gstFile, setGstFile] = useState<File | null>(null);
  const [gstValidation, setGstValidation] = useState<CsvValidationResponse | null>(null);
  const [gstCommitting, setGstCommitting] = useState(false);
  const [gstMsg, setGstMsg] = useState<string | null>(null);
  const [updateStockWithGst, setUpdateStockWithGst] = useState(true);
  const [showMappingModal, setShowMappingModal] = useState(false);
  const [newMapping, setNewMapping] = useState({ hsn_code: '', item_description: '', mapped_sku: '' });

  // --- 3. Stock Snapshots & Batches State ---
  const [stockBatches, setStockBatches] = useState<StockBatch[]>([]);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockFile, setStockFile] = useState<File | null>(null);
  const [stockMsg, setStockMsg] = useState<string | null>(null);

  // --- 4. Market Signals State ---
  const [marketSignals, setMarketSignals] = useState<MarketSignal[]>([]);
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketFile, setMarketFile] = useState<File | null>(null);
  const [marketMsg, setMarketMsg] = useState<string | null>(null);

  // Load Sales Data
  const loadSalesHistory = async () => {
    setSalesLoading(true);
    try {
      const res = await api.getSales({
        sku: salesSkuFilter,
        page: salesPage,
        per_page: 50
      });
      setSales(res.items);
      setSalesTotal(res.total);
    } catch (err: any) {
      console.error(err);
    } finally {
      setSalesLoading(false);
    }
  };

  // Load GST Data
  const loadGstData = async () => {
    setGstLoading(true);
    try {
      const res = await api.getGstLines({ per_page: 50 });
      setGstLines(res.items || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setGstLoading(false);
    }
  };

  // Load Stock Batches
  const loadStockData = async () => {
    setStockLoading(true);
    try {
      const batches = await api.getStockBatches();
      setStockBatches(batches || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setStockLoading(false);
    }
  };

  // Load Market Signals
  const loadMarketData = async () => {
    setMarketLoading(true);
    try {
      const signals = await api.getMarketSignals();
      setMarketSignals(signals || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setMarketLoading(false);
    }
  };

  useEffect(() => {
    if (topTab === 'sales') loadSalesHistory();
    else if (topTab === 'gst') loadGstData();
    else if (topTab === 'stock') loadStockData();
    else if (topTab === 'market') loadMarketData();
  }, [topTab, salesSkuFilter, salesPage]);

  // --- Sales CSV Handlers ---
  const handleSalesFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setSalesFile(file);
    setSalesValidation(null);
    setSalesMsg(null);
    try {
      const res = await api.validateSalesCsv(file);
      setSalesValidation(res);
    } catch (err: any) {
      alert(err?.message || 'CSV validation failed');
    }
  };

  const handleCommitSales = async () => {
    if (!salesValidation || !salesValidation.all_valid) return;
    setSalesCommitting(true);
    try {
      const res = await api.commitSalesImport(
        salesValidation.batch_id,
        salesValidation.filename,
        salesValidation.all_valid
      );
      setSalesMsg(res.message);
      setSalesValidation(null);
      setSalesFile(null);
      loadSalesHistory();
    } catch (err: any) {
      alert(err?.message || 'Failed to commit sales import');
    } finally {
      setSalesCommitting(false);
    }
  };

  // --- GST CSV Handlers ---
  const handleGstFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setGstFile(file);
    setGstValidation(null);
    setGstMsg(null);
    try {
      const res = await api.validateGstCsv(file);
      setGstValidation(res);
    } catch (err: any) {
      alert(err?.message || 'GST CSV validation failed');
    }
  };

  const handleCommitGst = async () => {
    if (!gstValidation || !gstValidation.all_valid) return;
    setGstCommitting(true);
    try {
      const res = await api.commitGstImport(
        gstValidation.batch_id,
        gstValidation.filename,
        gstValidation.all_valid,
        updateStockWithGst
      );
      setGstMsg(res.message);
      setGstValidation(null);
      setGstFile(null);
      loadGstData();
    } catch (err: any) {
      alert(err?.message || 'Failed to commit GST import');
    } finally {
      setGstCommitting(false);
    }
  };

  const handleAddMapping = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMapping.mapped_sku) return;
    try {
      await api.addGstMapping(newMapping);
      alert('HSN Mapping added successfully!');
      setShowMappingModal(false);
      setNewMapping({ hsn_code: '', item_description: '', mapped_sku: '' });
      loadGstData();
    } catch (err: any) {
      alert(err?.message || 'Failed to add mapping');
    }
  };

  // --- Stock CSV Handler ---
  const handleStockFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    try {
      const res = await api.importStockCsv(file);
      setStockMsg(res.message);
      loadStockData();
    } catch (err: any) {
      alert(err?.message || 'Stock import failed');
    }
  };

  // --- Market CSV Handler ---
  const handleMarketFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    try {
      const res = await api.importMarketCsv(file);
      setMarketMsg(res.message);
      loadMarketData();
    } catch (err: any) {
      alert(err?.message || 'Market signal import failed');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight flex items-center gap-2">
            <Database className="w-7 h-7 text-blue-600" />
            Data Ingestion & History
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Universal CSV ingestion hub: direct sales ledger, GST tax invoices, stock balance snapshots, and market trend signals.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href={api.getReportDownloadUrl('sales')}
            download
            className="px-3.5 py-2 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export Sales CSV</span>
          </a>
        </div>
      </div>

      {/* Main Tab Navigation */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setTopTab('sales')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            topTab === 'sales'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          Direct Sales History
        </button>
        <button
          onClick={() => setTopTab('gst')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            topTab === 'gst'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Receipt className="w-4 h-4" />
          GST Invoice Files
        </button>
        <button
          onClick={() => setTopTab('stock')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            topTab === 'stock'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Boxes className="w-4 h-4" />
          Stock Snapshots & Expiries
        </button>
        <button
          onClick={() => setTopTab('market')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            topTab === 'market'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Market Trend Signals
        </button>
      </div>

      {/* TAB 1: DIRECT SALES */}
      {topTab === 'sales' && (
        <div className="space-y-6">
          {/* Sales CSV Upload */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Upload className="w-4 h-4 text-blue-600" /> Sales CSV Ingestion & Pre-Flight Validation
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Format: <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-blue-700">sku,sale_date,quantity_sold</code>. Checks unknown SKUs, invalid dates, and prevents duplicate records.
                </p>
              </div>
            </div>

            <div className="border-2 border-dashed border-slate-200 hover:border-blue-400 transition-colors rounded-xl p-5 text-center bg-slate-50/50">
              <input
                type="file"
                id="sales-file-input"
                accept=".csv,text/csv"
                onChange={handleSalesFileSelect}
                className="hidden"
              />
              <label htmlFor="sales-file-input" className="cursor-pointer flex flex-col items-center gap-2">
                <Upload className="w-8 h-8 text-slate-400" />
                <span className="text-xs font-semibold text-slate-700">
                  {salesFile ? salesFile.name : 'Click to select Sales CSV file'}
                </span>
                <span className="text-[11px] text-slate-400">CSV files up to 10MB</span>
              </label>
            </div>

            {salesValidation && (
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3 animate-fade-in text-xs">
                <div className="flex items-center justify-between">
                  <div className="font-bold text-slate-900">Pre-Flight Validation Summary</div>
                  <div className="flex gap-2">
                    <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 font-semibold">
                      {salesValidation.valid_count} Valid
                    </span>
                    <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200 font-semibold">
                      {salesValidation.invalid_count} Invalid
                    </span>
                    <span className="text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full font-semibold">
                      {salesValidation.duplicate_count} Duplicates Skipped
                    </span>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
                  <button
                    onClick={handleCommitSales}
                    disabled={salesCommitting || salesValidation.valid_count === 0}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-xs transition-colors disabled:opacity-50"
                  >
                    {salesCommitting ? 'Importing...' : `Commit ${salesValidation.valid_count} Valid Records`}
                  </button>
                </div>
              </div>
            )}

            {salesMsg && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                {salesMsg}
              </div>
            )}
          </div>

          {/* Sales History Table */}
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="p-3.5 bg-slate-50/70 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter by SKU..."
                  value={salesSkuFilter}
                  onChange={e => {
                    setSalesSkuFilter(e.target.value);
                    setSalesPage(1);
                  }}
                  className="px-2.5 py-1 text-xs border border-slate-300 rounded-lg uppercase font-mono"
                />
              </div>
              <div className="text-xs text-slate-500 font-mono">
                Showing {sales.length} of {salesTotal} recorded sales
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-4">Sale Date</th>
                    <th className="py-2.5 px-4">SKU</th>
                    <th className="py-2.5 px-4">Product Name</th>
                    <th className="py-2.5 px-4">Category</th>
                    <th className="py-2.5 px-4 text-right">Quantity Sold</th>
                    <th className="py-2.5 px-4 text-center">Ingestion Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {sales.map((s, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 text-slate-600">{s.sale_date}</td>
                      <td className="py-2.5 px-4 font-bold text-blue-600">{s.sku}</td>
                      <td className="py-2.5 px-4 font-sans text-slate-900">{s.product_name}</td>
                      <td className="py-2.5 px-4 font-sans text-slate-500">{s.category}</td>
                      <td className="py-2.5 px-4 text-right font-bold text-slate-900">{s.quantity_sold} units</td>
                      <td className="py-2.5 px-4 text-center font-sans">
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-100 text-slate-700">
                          {s.source || 'CSV'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: GST TAX INVOICES */}
      {topTab === 'gst' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Receipt className="w-4 h-4 text-blue-600" /> GST Invoice File Ingestion (Outward & Inward)
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Universal GST CSV: outward supplies become sales history; inward supplies record purchase receipts.
                </p>
              </div>
              <button
                onClick={() => setShowMappingModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                HSN to SKU Mappings
              </button>
            </div>

            <div className="border-2 border-dashed border-slate-200 hover:border-blue-400 transition-colors rounded-xl p-5 text-center bg-slate-50/50">
              <input
                type="file"
                id="gst-file-input"
                accept=".csv,text/csv"
                onChange={handleGstFileSelect}
                className="hidden"
              />
              <label htmlFor="gst-file-input" className="cursor-pointer flex flex-col items-center gap-2">
                <Receipt className="w-8 h-8 text-slate-400" />
                <span className="text-xs font-semibold text-slate-700">
                  {gstFile ? gstFile.name : 'Click to select GST Invoice CSV'}
                </span>
                <span className="text-[11px] text-slate-400">Requires invoice_no, invoice_date, supply_type, hsn_code, quantity, taxable_value</span>
              </label>
            </div>

            {gstValidation && (
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3 animate-fade-in text-xs">
                <div className="flex items-center justify-between">
                  <div className="font-bold text-slate-900">GST Pre-Flight Validation</div>
                  <div className="flex gap-2">
                    <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 font-semibold">
                      {gstValidation.valid_count} Valid
                    </span>
                    <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200 font-semibold">
                      {gstValidation.invalid_count} Invalid
                    </span>
                    <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 font-semibold">
                      {gstValidation.unmapped_count || 0} Unmapped HSN
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-200">
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={updateStockWithGst}
                      onChange={e => setUpdateStockWithGst(e.target.checked)}
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    Reconcile stock balance from Inward (Purchase) supplies
                  </label>

                  <button
                    onClick={handleCommitGst}
                    disabled={gstCommitting || gstValidation.valid_count === 0}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-xs transition-colors disabled:opacity-50"
                  >
                    {gstCommitting ? 'Importing...' : `Commit ${gstValidation.valid_count} GST Records`}
                  </button>
                </div>
              </div>
            )}

            {gstMsg && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                {gstMsg}
              </div>
            )}
          </div>

          {/* GST Lines Ledger */}
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="p-3.5 bg-slate-50/70 border-b border-slate-200">
              <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Audited GST Invoice Lines ({gstLines.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left font-mono">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 font-sans">
                  <tr>
                    <th className="py-2.5 px-4">Invoice No</th>
                    <th className="py-2.5 px-4">Date</th>
                    <th className="py-2.5 px-4 text-center">Type</th>
                    <th className="py-2.5 px-4">HSN Code</th>
                    <th className="py-2.5 px-4">Mapped SKU</th>
                    <th className="py-2.5 px-4 text-right">Quantity</th>
                    <th className="py-2.5 px-4 text-right">Total Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {gstLines.map((line) => (
                    <tr key={line.id} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 font-bold text-slate-900">{line.invoice_no}</td>
                      <td className="py-2.5 px-4 text-slate-600">{line.invoice_date}</td>
                      <td className="py-2.5 px-4 text-center font-sans">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          line.supply_type === 'outward'
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}>
                          {line.supply_type.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">{line.hsn_code || '—'}</td>
                      <td className="py-2.5 px-4 font-bold text-blue-600">{line.sku || 'Unmapped'}</td>
                      <td className="py-2.5 px-4 text-right font-bold text-slate-800">{line.quantity}</td>
                      <td className="py-2.5 px-4 text-right font-bold text-slate-900">
                        ₹{line.total_value ? line.total_value.toFixed(2) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: STOCK SNAPSHOTS & BATCHES */}
      {topTab === 'stock' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Boxes className="w-4 h-4 text-blue-600" /> Stock Snapshot Ingestion & Batch Expiry Tracking
            </h2>
            <p className="text-xs text-slate-500">
              Columns: <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-blue-700">sku,quantity_on_hand,as_of_date,batch_id,expiry_date</code>. Reconciles current on-hand stock with inventory movements.
            </p>

            <div className="border-2 border-dashed border-slate-200 hover:border-blue-400 transition-colors rounded-xl p-5 text-center bg-slate-50/50">
              <input
                type="file"
                id="stock-file-input"
                accept=".csv,text/csv"
                onChange={handleStockFileSelect}
                className="hidden"
              />
              <label htmlFor="stock-file-input" className="cursor-pointer flex flex-col items-center gap-2">
                <Boxes className="w-8 h-8 text-slate-400" />
                <span className="text-xs font-semibold text-slate-700">
                  {stockFile ? stockFile.name : 'Click to select Stock Snapshot CSV'}
                </span>
                <span className="text-[11px] text-slate-400">Reconciles stock balances and records perishable expiry dates</span>
              </label>
            </div>

            {stockMsg && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                {stockMsg}
              </div>
            )}
          </div>

          {/* Batches Table */}
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="p-3.5 bg-slate-50/70 border-b border-slate-200">
              <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Current Monitored Batches & Expiry Dates ({stockBatches.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left font-mono">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 font-sans">
                  <tr>
                    <th className="py-2.5 px-4">SKU</th>
                    <th className="py-2.5 px-4">Product Name</th>
                    <th className="py-2.5 px-4">Batch ID</th>
                    <th className="py-2.5 px-4 text-right">Units in Batch</th>
                    <th className="py-2.5 px-4 text-center">Expiry Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {stockBatches.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 font-bold text-blue-600">{b.sku}</td>
                      <td className="py-2.5 px-4 font-sans text-slate-900">{b.product_name}</td>
                      <td className="py-2.5 px-4 text-slate-600">{b.batch_id}</td>
                      <td className="py-2.5 px-4 text-right font-bold text-slate-900">{b.quantity}</td>
                      <td className="py-2.5 px-4 text-center font-sans">
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                          {b.expiry_date}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: MARKET SIGNALS */}
      {topTab === 'market' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600" /> External Market Signals Ingestion
            </h2>
            <p className="text-xs text-slate-500">
              Columns: <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-blue-700">date,sku_or_category,signal_type,value,notes</code>. Bounded adjustment (0.80x to 1.40x) on forward forecasts.
            </p>

            <div className="border-2 border-dashed border-slate-200 hover:border-blue-400 transition-colors rounded-xl p-5 text-center bg-slate-50/50">
              <input
                type="file"
                id="market-file-input"
                accept=".csv,text/csv"
                onChange={handleMarketFileSelect}
                className="hidden"
              />
              <label htmlFor="market-file-input" className="cursor-pointer flex flex-col items-center gap-2">
                <TrendingUp className="w-8 h-8 text-slate-400" />
                <span className="text-xs font-semibold text-slate-700">
                  {marketFile ? marketFile.name : 'Click to select Market Signals CSV'}
                </span>
                <span className="text-[11px] text-slate-400">Festival events, price index changes, and localized demand shifts</span>
              </label>
            </div>

            {marketMsg && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                {marketMsg}
              </div>
            )}
          </div>

          {/* Market Signals Table */}
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="p-3.5 bg-slate-50/70 border-b border-slate-200">
              <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Active Market Signals ({marketSignals.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left font-mono">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 font-sans">
                  <tr>
                    <th className="py-2.5 px-4">Date</th>
                    <th className="py-2.5 px-4">Target Scope</th>
                    <th className="py-2.5 px-4">Signal Type</th>
                    <th className="py-2.5 px-4 text-right">Value</th>
                    <th className="py-2.5 px-4 font-sans">Notes / Context</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {marketSignals.map((sig) => (
                    <tr key={sig.id} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-4 text-slate-600">{sig.date}</td>
                      <td className="py-2.5 px-4 font-bold text-blue-600">{sig.scope_value}</td>
                      <td className="py-2.5 px-4 text-slate-800">{sig.signal_type}</td>
                      <td className="py-2.5 px-4 text-right font-bold text-slate-900">{sig.value}</td>
                      <td className="py-2.5 px-4 font-sans text-slate-500">{sig.notes || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* HSN to SKU Mapping Modal */}
      {showMappingModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full overflow-hidden animate-scale-in">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Receipt className="w-4 h-4 text-blue-600" />
                Add HSN / Description Mapping
              </h2>
              <button
                onClick={() => setShowMappingModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleAddMapping} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">HSN Code</label>
                <input
                  type="text"
                  placeholder="e.g. 0401 or 1006"
                  value={newMapping.hsn_code}
                  onChange={e => setNewMapping({ ...newMapping, hsn_code: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Item Description Keyword (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Fresh Milk or Basmati"
                  value={newMapping.item_description}
                  onChange={e => setNewMapping({ ...newMapping, item_description: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Target Product SKU *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. MLK-001"
                  value={newMapping.mapped_sku}
                  onChange={e => setNewMapping({ ...newMapping, mapped_sku: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg uppercase font-mono"
                />
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowMappingModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold shadow-xs"
                >
                  Save Mapping
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
