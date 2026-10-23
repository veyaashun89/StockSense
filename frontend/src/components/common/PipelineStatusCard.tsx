import React, { useState } from 'react';
import { Activity, Play, CheckCircle2, AlertCircle, Clock, FolderSync, Sparkles } from 'lucide-react';
import { api } from '../../services/api';

interface PipelineStatusCardProps {
  statusData?: any;
  onPipelineRun?: () => void;
}

export const PipelineStatusCard: React.FC<PipelineStatusCardProps> = ({ statusData, onPipelineRun }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);

  const handleTriggerRun = async () => {
    setIsRunning(true);
    setRunMessage(null);
    try {
      const res = await api.runPipeline();
      setRunMessage(
        `Pipeline finished (${res.status}): ${res.files_processed_count} files processed (${res.rows_processed} rows). Alerts refreshed.`
      );
      if (onPipelineRun) onPipelineRun();
    } catch (err: any) {
      setRunMessage(err.message || 'Pipeline execution failed');
    } finally {
      setIsRunning(false);
    }
  };

  const latest = statusData?.latest_run;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <FolderSync className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
              Automated Data Pipeline
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping inline-block" />
            </h3>
            <p className="text-[11px] text-slate-500">
              Watched Folder: <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-slate-700">data_inbox/</code> (Auto-detects GST, Sales, Stock, Market CSVs)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleTriggerRun}
            disabled={isRunning}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-all disabled:opacity-50"
          >
            <Play className={`w-3 h-3 fill-white ${isRunning ? 'animate-spin' : ''}`} />
            <span>{isRunning ? 'Processing...' : 'Run Pipeline Now'}</span>
          </button>
        </div>
      </div>

      {runMessage && (
        <div className="mt-3 p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
          <span>{runMessage}</span>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3 text-xs">
        <div>
          <span className="text-slate-400 text-[11px]">Last Run Status</span>
          <p className="font-bold text-slate-800 flex items-center gap-1 mt-0.5">
            {latest?.status === 'SUCCESS' ? (
              <span className="text-emerald-700 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Success
              </span>
            ) : latest?.status ? (
              <span className="text-amber-700 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" /> {latest.status}
              </span>
            ) : (
              <span className="text-slate-500">Ready</span>
            )}
          </p>
        </div>

        <div>
          <span className="text-slate-400 text-[11px]">Rows Ingested</span>
          <p className="font-bold text-slate-800 mt-0.5 tabular-nums">
            {latest?.rows_processed ?? 0} rows
          </p>
        </div>

        <div>
          <span className="text-slate-400 text-[11px]">Trigger Mode</span>
          <p className="font-bold text-slate-800 mt-0.5">
            {latest?.triggered_by ?? 'Automated Watcher'}
          </p>
        </div>

        <div>
          <span className="text-slate-400 text-[11px]">Execution Time</span>
          <p className="font-medium text-slate-600 mt-0.5">
            {latest?.finished_at ? new Date(latest.finished_at).toLocaleTimeString() : 'Active'}
          </p>
        </div>
      </div>
    </div>
  );
};
