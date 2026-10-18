import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'cyan' | 'crimson' | 'amber' | 'emerald' | 'purple' | 'slate';
  size?: 'sm' | 'md';
  pulse?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'cyan',
  size = 'sm',
  pulse = false,
  className = '',
}) => {
  const variantStyles = {
    cyan: 'bg-cyan-950/70 text-cyan-400 border-cyan-800/60',
    crimson: 'bg-red-950/70 text-red-400 border-red-800/60',
    amber: 'bg-amber-950/70 text-amber-400 border-amber-800/60',
    emerald: 'bg-emerald-950/70 text-emerald-400 border-emerald-800/60',
    purple: 'bg-purple-950/70 text-purple-400 border-purple-800/60',
    slate: 'bg-slate-900 text-slate-400 border-slate-800',
  };

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5 tracking-wide',
    md: 'text-xs px-2.5 py-1',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-full uppercase font-mono ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {pulse && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-current"></span>
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current"></span>
        </span>
      )}
      {children}
    </span>
  );
};
