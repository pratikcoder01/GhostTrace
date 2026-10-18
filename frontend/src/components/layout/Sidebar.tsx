import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderPlus,
  GitBranch,
  AlertTriangle,
  Search,
  Wallet,
  TrendingDown,
  Shield,
  FileText,
  Activity,
  Brain,
  Grid3X3,
  Layers,
  ChevronLeft,
  ChevronRight,
  Ghost,
  Menu,
  X,
} from 'lucide-react';

export interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { path: '/new-case', label: 'New Case', icon: <FolderPlus className="w-5 h-5" /> },
  { path: '/graph', label: 'Transaction Graph', icon: <GitBranch className="w-5 h-5" /> },
  { path: '/matrices', label: 'Matrices & Tensors', icon: <Grid3X3 className="w-5 h-5" /> },
  { path: '/exposure', label: 'Exposure & Exit Paths', icon: <Layers className="w-5 h-5" /> },
  { path: '/triage', label: 'ML Triage & Predict', icon: <Brain className="w-5 h-5" /> },
  { path: '/leads', label: 'Investigative Leads', icon: <AlertTriangle className="w-5 h-5" /> },
  { path: '/osint', label: 'OSINT Intelligence', icon: <Search className="w-5 h-5" /> },
  { path: '/wallets', label: 'Wallet Explorer', icon: <Wallet className="w-5 h-5" /> },
  { path: '/cashout', label: 'Cash-out Forecast', icon: <TrendingDown className="w-5 h-5" /> },
  { path: '/audit', label: 'Audit Chain', icon: <Shield className="w-5 h-5" /> },
  { path: '/reports', label: 'Reports & Export', icon: <FileText className="w-5 h-5" /> },
  { path: '/benchmark', label: 'Model Health', icon: <Activity className="w-5 h-5" /> },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle, mobileOpen, onMobileClose }) => {
  const location = useLocation();

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={onMobileClose}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed top-0 left-0 h-full z-50 flex flex-col
          bg-[#0b0f1c] border-r border-[#1a2336]
          transition-all duration-300 ease-in-out
          ${collapsed ? 'w-[64px]' : 'w-[240px]'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Logo */}
        <div className={`flex items-center h-14 px-4 border-b border-[#1a2336] shrink-0 ${collapsed ? 'justify-center' : 'gap-3'}`}>
          <div className="w-8 h-8 rounded-lg bg-cyan-900/60 border border-cyan-700/60 flex items-center justify-center shrink-0">
            <Ghost className="w-5 h-5 text-cyan-400" />
          </div>
          {!collapsed && (
            <div>
              <div className="text-white font-bold text-sm tracking-widest">GHOSTTRACE</div>
              <div className="text-[10px] text-cyan-500/80 tracking-widest uppercase">Forensic Intelligence</div>
            </div>
          )}
          {/* Mobile close */}
          <button
            className="ml-auto lg:hidden text-slate-400 hover:text-white"
            onClick={onMobileClose}
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 scrollbar-thin">
          {!collapsed && (
            <div className="px-3 mb-2">
              <span className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest">Investigation</span>
            </div>
          )}
          {NAV_ITEMS.map((item) => {
            const isActive = item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={onMobileClose}
                title={collapsed ? item.label : undefined}
                className={`
                  flex items-center mx-2 px-3 py-2.5 mb-0.5 rounded-md
                  text-sm font-medium transition-all duration-150 group
                  ${collapsed ? 'justify-center' : 'gap-3'}
                  ${isActive
                    ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/50 shadow-sm'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-100 border border-transparent'
                  }
                `}
              >
                <span className={isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-300 transition-colors'}>
                  {item.icon}
                </span>
                {!collapsed && <span className="truncate">{item.label}</span>}
                {!collapsed && item.badge && (
                  <span className="ml-auto text-[10px] font-bold bg-red-900 text-red-300 rounded px-1 py-0.5 border border-red-800">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle (desktop) */}
        <div className="hidden lg:flex px-3 py-3 border-t border-[#1a2336]">
          <button
            onClick={onToggle}
            className="flex items-center gap-2 text-slate-500 hover:text-slate-200 text-xs transition-colors w-full"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4 mx-auto" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>
    </>
  );
};

// Mobile hamburger button exported for TopBar
export const MobileMenuButton: React.FC<{ onClick: () => void }> = ({ onClick }) => (
  <button
    className="lg:hidden text-slate-400 hover:text-white p-1 rounded"
    onClick={onClick}
    aria-label="Open menu"
  >
    <Menu className="w-5 h-5" />
  </button>
);
