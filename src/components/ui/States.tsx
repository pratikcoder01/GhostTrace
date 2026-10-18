import React from 'react';
import { AlertTriangle, WifiOff, RefreshCw } from 'lucide-react';
import { Button } from './Button';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  isOffline?: boolean;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to load data',
  message = 'Failed to fetch from the GhostTrace backend.',
  onRetry,
  isOffline = false,
}) => {
  const Icon = isOffline ? WifiOff : AlertTriangle;
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="w-14 h-14 rounded-full bg-red-950/60 border border-red-800/60 flex items-center justify-center">
        <Icon className="w-7 h-7 text-red-400" />
      </div>
      <div>
        <div className="text-slate-200 font-semibold">{title}</div>
        <div className="text-slate-400 text-sm mt-1 max-w-sm">{message}</div>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" icon={<RefreshCw className="w-4 h-4" />} onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
};

export const EmptyState: React.FC<{
  icon?: React.ReactNode;
  title?: string;
  message?: string;
  action?: React.ReactNode;
}> = ({
  icon,
  title = 'No data available',
  message = 'Nothing to display at the moment.',
  action,
}) => (
  <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
    {icon && (
      <div className="w-14 h-14 rounded-full bg-slate-800/60 border border-slate-700/60 flex items-center justify-center text-slate-500">
        {icon}
      </div>
    )}
    <div>
      <div className="text-slate-300 font-semibold">{title}</div>
      <div className="text-slate-500 text-sm mt-1 max-w-sm">{message}</div>
    </div>
    {action}
  </div>
);

export const LoadingState: React.FC<{ message?: string }> = ({ message = 'Loading…' }) => (
  <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
    <div className="w-10 h-10 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
    <div className="text-slate-400 text-sm">{message}</div>
  </div>
);
