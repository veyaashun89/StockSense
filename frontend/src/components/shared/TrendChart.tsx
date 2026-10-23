import React, { useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import { Table, Eye } from 'lucide-react';

export interface TrendDataPoint {
  date: string;
  value: number;
  secondaryValue?: number;
  label?: string;
}

interface TrendChartProps {
  title: string;
  subtitle?: string;
  data: TrendDataPoint[];
  dataKey?: string;
  secondaryDataKey?: string;
  dataLabel?: string;
  secondaryDataLabel?: string;
  height?: number;
  currencyPrefix?: string;
  className?: string;
}

export const TrendChart: React.FC<TrendChartProps> = ({
  title,
  subtitle,
  data,
  dataKey = 'value',
  secondaryDataKey,
  dataLabel = 'Primary Metric',
  secondaryDataLabel = 'Secondary Metric',
  height = 240,
  currencyPrefix = '',
  className = ''
}) => {
  const [showTable, setShowTable] = useState(false);

  return (
    <div
      role="region"
      aria-label={title}
      className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 sm:p-5 shadow-xs ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
            {title}
          </h3>
          {subtitle && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>
          )}
        </div>

        {/* Accessible Data Table Toggle Button */}
        <button
          onClick={() => setShowTable(!showTable)}
          aria-expanded={showTable}
          aria-label="Toggle accessible data table view for chart"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 transition-colors self-start sm:self-center"
        >
          <Table className="w-3.5 h-3.5" aria-hidden="true" />
          <span>{showTable ? 'Show Chart' : 'Accessible Table'}</span>
        </button>
      </div>

      {showTable ? (
        /* Accessible HTML5 Data Table */
        <div className="overflow-x-auto max-h-60 border border-slate-200 dark:border-slate-800 rounded-lg">
          <table className="w-full text-left text-xs">
            <caption className="sr-only">{title} data series</caption>
            <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th scope="col" className="p-2.5">Date / Timeline</th>
                <th scope="col" className="p-2.5 text-right">{dataLabel}</th>
                {secondaryDataKey && (
                  <th scope="col" className="p-2.5 text-right">{secondaryDataLabel}</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300 font-mono">
              {data.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                  <td className="p-2.5">{row.date}</td>
                  <td className="p-2.5 text-right tabular-nums font-bold">
                    {currencyPrefix}{row[dataKey as keyof TrendDataPoint] ?? 0}
                  </td>
                  {secondaryDataKey && (
                    <td className="p-2.5 text-right tabular-nums text-slate-500">
                      {currencyPrefix}{row[secondaryDataKey as keyof TrendDataPoint] ?? 0}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Visual Recharts Area */
        <div style={{ width: '100%', height }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="primaryTrendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563EB" stopOpacity={0.28} />
                  <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
                </linearGradient>
                {secondaryDataKey && (
                  <linearGradient id="secondaryTrendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.28} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                  </linearGradient>
                )}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: '#64748B' }}
                tickLine={false}
                axisLine={{ stroke: '#E2E8F0' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#64748B' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-slate-900 text-white p-2.5 rounded-lg text-xs shadow-lg space-y-1">
                        <p className="font-semibold text-slate-300">{label}</p>
                        {payload.map((p: any, idx: number) => (
                          <p key={idx} style={{ color: p.color }}>
                            {p.name}: <span className="font-bold tabular-nums">{currencyPrefix}{p.value}</span>
                          </p>
                        ))}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey={dataKey}
                name={dataLabel}
                stroke="#2563EB"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#primaryTrendGrad)"
              />
              {secondaryDataKey && (
                <Area
                  type="monotone"
                  dataKey={secondaryDataKey}
                  name={secondaryDataLabel}
                  stroke="#10B981"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  fillOpacity={1}
                  fill="url(#secondaryTrendGrad)"
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};
