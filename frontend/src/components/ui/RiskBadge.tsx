import React from 'react';
import { getRiskColor } from '@/lib/utils';

interface RiskBadgeProps {
  level?: string;
  score?: number;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, score, className = '' }) => {
  const colors = getRiskColor(level);
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[11px] font-bold uppercase tracking-wider font-mono ${colors.bg} ${colors.text} ${colors.border} ${className}`}
    >
      {level || 'Unknown'}
      {score !== undefined && (
        <span className="opacity-80 font-normal">{score.toFixed(0)}</span>
      )}
    </span>
  );
};

export const StatusDot: React.FC<{
  status: 'online' | 'offline' | 'warning' | 'unknown';
  label?: string;
}> = ({ status, label }) => {
  const styles = {
    online: 'bg-emerald-400',
    offline: 'bg-red-400',
    warning: 'bg-amber-400',
    unknown: 'bg-slate-500',
  };
  return (
    <span className="inline-flex items-center gap-2 text-xs text-slate-400">
      <span className={`w-2 h-2 rounded-full ${styles[status]} ${status === 'online' ? 'animate-pulse' : ''}`} />
      {label}
    </span>
  );
};
