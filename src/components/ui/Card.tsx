import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  headerClassName?: string;
  bodyClassName?: string;
  highlight?: 'cyan' | 'crimson' | 'amber' | 'none';
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  action,
  className = '',
  headerClassName = '',
  bodyClassName = '',
  highlight = 'none',
}) => {
  const highlightStyles = {
    none: 'border-[#1e293b]',
    cyan: 'border-cyan-800/60 shadow-[0_0_15px_rgba(6,182,212,0.05)]',
    crimson: 'border-red-900/60 shadow-[0_0_15px_rgba(239,68,68,0.05)]',
    amber: 'border-amber-900/60 shadow-[0_0_15px_rgba(245,158,11,0.05)]',
  };

  return (
    <div
      className={`bg-[#101624] border rounded-lg overflow-hidden transition-all duration-200 ${highlightStyles[highlight]} ${className}`}
    >
      {(title || subtitle || action) && (
        <div
          className={`px-5 py-4 border-b border-[#1a2336] flex items-center justify-between gap-4 bg-[#0d121f]/50 ${headerClassName}`}
        >
          <div>
            {title && <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">{title}</h3>}
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className={`p-5 ${bodyClassName}`}>{children}</div>
    </div>
  );
};
