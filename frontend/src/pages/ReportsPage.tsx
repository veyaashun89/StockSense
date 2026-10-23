import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  Printer,
  Table,
  AlertTriangle,
  Clock,
  ShoppingCart,
  Package,
  Layers
} from 'lucide-react';
import { api } from '../services/api';

interface ReportsPageProps {
  currencySymbol?: string;
}

export const ReportsPage: React.FC<ReportsPageProps> = ({ currencySymbol = '$' }) => {
  const [activeReport, setActiveReport] = useState<string>('reorder');
  const [reportData, setReportData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const reportTabs = [
    { id: 'reorder', label: 'Ranked Reorder Report', icon: ShoppingCart },
    { id: 'inventory', label: 'Current Inventory Status', icon: Package },
    { id: 'sales', label: 'Historical Sales Audit', icon: Table },
    { id: 'stockout', label: 'Stockout Risk Assessment', icon: AlertTriangle },
    { id: 'expiry', label: 'Perishable Expiry Risks', icon: Clock }
  ];

  const fetchReport = async (type: string) => {
    setLoading(true);
    try {
      const res = await api.getReportData(type);
      setReportData(res.data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport(activeReport);
  }, [activeReport]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight">Executive Reports & Audits</h1>
          <p className="text-sm text-slate-500 mt-1">
            Generate and export operational purchasing, inventory valuation, and stockout risk sheets.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handlePrint}
            className="px-3.5 py-2 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Printer className="w-3.5 h-3.5 text-slate-500" />
            <span>Print View</span>
          </button>
          <a
            href={api.getReportDownloadUrl(activeReport)}
            download
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-bold shadow-sm shadow-blue-500/20 hover:bg-blue-700 transition-colors flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download CSV</span>
          </a>
        </div>
      </div>

      {/* Report Selector Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        {reportTabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeReport === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveReport(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Report Table Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between">
          <div className="text-xs text-slate-600">
            Active Dataset: <span className="font-bold text-slate-800">{reportTabs.find(t => t.id === activeReport)?.label}</span>{' '}
            ({reportData.length} rows)
          </div>
          <div className="text-[11px] text-slate-400">
            Generated: {new Date().toLocaleDateString()} {new Date().toLocaleTimeString()}
          </div>
        </div>

        <div className="overflow-x-auto max-h-[600px]">
          {loading ? (
            <div className="py-16 text-center text-xs text-slate-400">Loading operational report...</div>
          ) : reportData.length === 0 ? (
            <div className="py-16 text-center text-xs text-slate-500">No records found for this report.</div>
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 sticky top-0 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                <tr>
                  {Object.keys(reportData[0])
                    .filter(k => !['signals', 'calculation_trace', 'all_reasons', 'product_id'].includes(k))
                    .map(colKey => (
                      <th key={colKey} className="py-3 px-4">
                        {colKey.replace(/_/g, ' ')}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {reportData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    {Object.entries(row)
                      .filter(([k]) => !['signals', 'calculation_trace', 'all_reasons', 'product_id'].includes(k))
                      .map(([key, val]: any, cellIdx) => (
                        <td key={cellIdx} className="py-2.5 px-4 tabular-nums">
                          {typeof val === 'number'
                            ? val.toLocaleString()
                            : typeof val === 'boolean'
                            ? val ? 'Yes' : 'No'
                            : val ?? '—'}
                        </td>
                      ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
