import React, { useEffect, useState } from 'react';
import { Bell, Settings, User, RefreshCw, AlertCircle, CheckCircle2, Radio, Activity, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api, parseApiError } from '@/api/client';
import { HealthResponse } from '@/types/api';
import { useWebSocket } from '@/context/WebSocketContext';
import { MobileMenuButton } from './Sidebar';

interface TopBarProps {
  sidebarCollapsed: boolean;
  onMobileMenuOpen: () => void;
  activeCaseId?: string;
}

export const TopBar: React.FC<TopBarProps> = ({ sidebarCollapsed, onMobileMenuOpen, activeCaseId }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const { connectionStatus, providerStatus, lastEventTime } = useWebSocket();

  const fetchHealth = async () => {
    setRefreshing(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
      setHealthError(null);
    } catch (err) {
      setHealthError(parseApiError(err));
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const sidebarWidth = sidebarCollapsed ? '64px' : '240px';

  return (
    <header
      className="fixed top-0 right-0 h-14 z-30 flex items-center gap-3 px-4 border-b border-[#1a2336] bg-[#0b0f1c]/95 backdrop-blur-md transition-all duration-300"
      style={{ left: sidebarWidth }}
    >
      <MobileMenuButton onClick={onMobileMenuOpen} />

      {/* Active Case indicator */}
      {activeCaseId && (
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 bg-cyan-950/50 border border-cyan-800/40 rounded text-xs text-cyan-300 font-mono">
          <span className="text-slate-500">ACTIVE:</span>
          <span className="truncate max-w-[120px]">{activeCaseId.substring(0, 8)}…</span>
        </div>
      )}

      {/* Real-Time WebSocket Connection Badge */}
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs border font-mono tracking-wide">
        {connectionStatus === 'connected' ? (
          <span className="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/40 border-emerald-800/50">
            <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-400" />
            <span className="font-semibold">LIVE WS</span>
          </span>
        ) : connectionStatus === 'reconnecting' ? (
          <span className="flex items-center gap-1.5 text-amber-400 bg-amber-950/40 border-amber-800/50">
            <Activity className="w-3.5 h-3.5 animate-spin text-amber-400" />
            <span>RECONNECTING</span>
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-red-400 bg-red-950/40 border-red-800/50">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            <span>WS OFFLINE</span>
          </span>
        )}
      </div>

      {/* Provider & Ingestion Lag Indicator */}
      {providerStatus && (
        <div className="hidden lg:flex items-center gap-2 text-xs border border-[#1a2336] bg-[#0d1220] px-2.5 py-1 rounded">
          <span className="text-slate-500">PROVIDER:</span>
          <span className={providerStatus.is_simulated ? "text-amber-400" : "text-cyan-400"}>
            {providerStatus.is_simulated ? "SIMULATOR" : providerStatus.provider_name.split(' ')[0]}
          </span>
          {providerStatus.last_processed_block && (
            <span className="text-slate-400 font-mono">#{providerStatus.last_processed_block}</span>
          )}
          {providerStatus.ingestion_lag > 0 && (
            <span className="text-amber-400 bg-amber-950/50 px-1.5 py-0.2 rounded text-[10px]">
              {providerStatus.ingestion_lag} blk lag
            </span>
          )}
        </div>
      )}

      <div className="flex-1" />

      {/* System Health */}
      <div className="hidden sm:flex items-center gap-2">
        {healthError ? (
          <span className="flex items-center gap-1.5 text-xs text-red-400 border border-red-900/60 bg-red-950/40 px-2.5 py-1 rounded">
            <AlertCircle className="w-3.5 h-3.5" />
            Backend Offline
          </span>
        ) : health ? (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400 border border-emerald-900/60 bg-emerald-950/40 px-2.5 py-1 rounded">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {health.service} v{health.version}
          </span>
        ) : (
          <span className="text-xs text-slate-500">Connecting…</span>
        )}
        <button
          onClick={fetchHealth}
          className="text-slate-500 hover:text-slate-200 p-1.5 rounded hover:bg-slate-800 transition-colors"
          aria-label="Refresh health"
          disabled={refreshing}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* TraceChain status */}
      {health && (
        <div className="hidden md:flex items-center gap-1.5 text-xs border border-[#1a2336] bg-[#0d1220] px-2.5 py-1 rounded">
          <div className={`w-1.5 h-1.5 rounded-full ${health.tracechain.integrity_valid ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
          <span className="text-slate-500">Chain:</span>
          <span className={health.tracechain.integrity_valid ? 'text-emerald-400' : 'text-red-400'}>
            {health.tracechain.block_height} blocks
          </span>
        </div>
      )}

      <div className="flex items-center gap-1">
        <button
          className="relative text-slate-400 hover:text-slate-200 p-1.5 rounded hover:bg-slate-800 transition-colors"
          aria-label="Notifications"
        >
          <Bell className="w-4.5 h-4.5" />
        </button>
        <Link
          to="/benchmark"
          className="text-slate-400 hover:text-slate-200 p-1.5 rounded hover:bg-slate-800 transition-colors"
          aria-label="Settings & Model Health"
        >
          <Settings className="w-4.5 h-4.5" />
        </Link>
        <button className="ml-1 w-8 h-8 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-slate-300 hover:bg-slate-600 transition-colors">
          <User className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
