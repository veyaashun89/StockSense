import React from 'react';

interface SkeletonBlockProps {
  className?: string;
  count?: number;
}

export const SkeletonBlock: React.FC<SkeletonBlockProps> = ({ className = 'h-6 w-full', count = 1 }) => {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-2.5 w-full">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`bg-slate-200 dark:bg-slate-800 animate-pulse rounded-lg ${className}`}
        />
      ))}
    </div>
  );
};
