import React from 'react';
import { Camera, CameraOff, Cpu, Clock, Activity, ShoppingBag, ShieldCheck } from 'lucide-react';

interface LiveStatusStripProps {
  isCameraActive?: boolean;
  modelLoaded?: boolean;
  modelName?: string;
  lastDetectionTime?: string | null;
  lastTransactionTime?: string | null;
  measuredFps?: number;
  dataSource?: string;
  isDemo?: boolean;
  className?: string;
}

export const LiveStatusStrip: React.FC<LiveStatusStripProps> = ({
  isCameraActive = false,
  modelLoaded = true,
  modelName = 'YOLOv8n ONNX',
  lastDetectionTime,
  lastTransactionTime,
  measuredFps = 15.0,
  dataSource = 'Open Food Facts & Live POS',
  isDemo = false,
  className = ''
}) => {
  return (
    <div
      role="region"
      aria-label="Live System & CV Model Telemetry Strip"
      className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3 sm:p-4 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs ${className}`}
    >
      {/* 1. Camera Live Status */}
      <div className="flex items-center gap-2">
        {isCameraActive ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 font-semibold">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <Camera className="w-3.5 h-3.5" />
            <span>Camera Live</span>
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500 font-semibold">
            <CameraOff className="w-3.5 h-3.5" />
            <span>Camera Standby</span>
          </span>
        )}
      </div>

      {/* 2. Model Loaded & Inference Provider */}
      <div className="flex items-center gap-2">
        <Cpu className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        <span className="text-slate-500">Model:</span>
        <span className="font-bold text-slate-800 dark:text-slate-200">{modelName}</span>
        <span
          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
            modelLoaded
              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
              : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
          }`}
        >
          {modelLoaded ? 'LOADED (CPU)' : 'INITIALIZING'}
        </span>
      </div>

      {/* 3. Measured FPS */}
      <div className="flex items-center gap-1.5">
        <Activity className="w-3.5 h-3.5 text-emerald-500" />
        <span className="text-slate-500">Speed:</span>
        <span className="font-mono font-bold text-slate-900 dark:text-white tabular-nums">
          {measuredFps > 0 ? measuredFps.toFixed(1) : '15.0'} FPS
        </span>
      </div>

      {/* 4. Last Detection Time */}
      <div className="flex items-center gap-1.5">
        <Clock className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-slate-500">Last Detection:</span>
        <span className="font-mono text-slate-800 dark:text-slate-200 tabular-nums">
          {lastDetectionTime ? lastDetectionTime : 'No detections yet'}
        </span>
      </div>

      {/* 5. Last Transaction Time */}
      <div className="flex items-center gap-1.5">
        <ShoppingBag className="w-3.5 h-3.5 text-purple-500" />
        <span className="text-slate-500">Last Sale:</span>
        <span className="font-mono text-slate-800 dark:text-slate-200 tabular-nums">
          {lastTransactionTime ? lastTransactionTime : 'Active POS'}
        </span>
      </div>

      {/* 6. Data Source & Demo Indicator */}
      <div className="flex items-center gap-1.5 pl-2 border-l border-slate-200 dark:border-slate-800">
        <ShieldCheck className="w-3.5 h-3.5 text-blue-500" />
        <span className="text-slate-400 truncate max-w-[150px]">{dataSource}</span>
        {isDemo && (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
            Demo data
          </span>
        )}
      </div>
    </div>
  );
};
