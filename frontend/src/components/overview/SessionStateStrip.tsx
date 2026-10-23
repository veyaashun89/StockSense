import React from 'react';
import { Activity, ShieldCheck, CheckCircle2, ChevronRight, Cpu } from 'lucide-react';

interface SessionStateStripProps {
  currentState: string;
  modelStatus?: string;
  measuredFps?: number;
  className?: string;
}

const STEPS = ['IDLE', 'SCANNING', 'BASKET', 'PAYMENT_PENDING', 'PAID', 'RECORDING'];

export const SessionStateStrip: React.FC<SessionStateStripProps> = ({
  currentState = 'IDLE',
  modelStatus = 'ACTIVE',
  measuredFps = 15.0,
  className = ''
}) => {
  const normState = currentState.toUpperCase();
  const currentIndex = STEPS.indexOf(normState) !== -1 ? STEPS.indexOf(normState) : 0;

  return (
    <div
      role="region"
      aria-label="POS Session State and Detection Model Telemetry"
      className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 sm:p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3 ${className}`}
    >
      {/* 1. Visible Step Indicator */}
      <div className="flex items-center gap-1 sm:gap-2 overflow-x-auto py-1">
        {STEPS.map((step, idx) => {
          const isActive = idx === currentIndex;
          const isPassed = idx < currentIndex;

          return (
            <React.Fragment key={step}>
              <div
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-xs ring-2 ring-blue-500/30'
                    : isPassed
                    ? 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                    : 'text-slate-400 dark:text-slate-600 bg-slate-50 dark:bg-slate-900/50'
                }`}
              >
                {isPassed ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" />
                ) : (
                  <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />
                )}
                <span>{step.replace('_', ' ')}</span>
              </div>
              {idx < STEPS.length - 1 && (
                <ChevronRight className="w-3 h-3 text-slate-300 dark:text-slate-700 shrink-0" aria-hidden="true" />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* 2. Model Status & Measured FPS */}
      <div className="flex items-center gap-3 text-xs shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" aria-hidden="true" />
          <span className="text-slate-500">Model:</span>
          <span className="font-bold text-slate-800 dark:text-slate-200">YOLOv8n ONNX</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
            {modelStatus}
          </span>
        </div>

        <div className="flex items-center gap-1.5 pl-3 border-l border-slate-200 dark:border-slate-800">
          <Activity className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          <span className="text-slate-500">Speed:</span>
          <span className="font-bold font-mono text-slate-900 dark:text-white tabular-nums">
            {measuredFps.toFixed(1)} FPS CPU
          </span>
        </div>
      </div>
    </div>
  );
};
