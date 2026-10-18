import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  icon,
  className = '',
  disabled,
  ...props
}) => {
  const baseClasses =
    'inline-flex items-center justify-center font-medium transition-all duration-150 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0a0d14] disabled:opacity-50 disabled:cursor-not-allowed select-none';

  const sizeClasses = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-3.5 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
  };

  const variantClasses = {
    primary:
      'bg-cyan-600 hover:bg-cyan-500 text-white shadow-sm hover:shadow-[0_0_15px_rgba(6,182,212,0.3)] focus:ring-cyan-500 border border-cyan-500/30',
    secondary:
      'bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/60 focus:ring-slate-500',
    danger:
      'bg-red-950/80 hover:bg-red-900/90 text-red-200 border border-red-700/60 focus:ring-red-600 shadow-sm',
    ghost:
      'bg-transparent hover:bg-slate-800/60 text-slate-300 hover:text-white focus:ring-slate-600',
    outline:
      'bg-transparent border border-slate-700 text-slate-300 hover:bg-slate-800/50 hover:border-slate-600 focus:ring-slate-500',
  };

  return (
    <button
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          <span>{children}</span>
        </>
      ) : (
        <>
          {icon && <span className="shrink-0">{icon}</span>}
          <span>{children}</span>
        </>
      )}
    </button>
  );
};
