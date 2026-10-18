import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  FolderOpen,
  GitBranch,
  AlertTriangle,
  Database,
  Cpu,
  TrendingUp,
  ArrowRight,
  Clock,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { api, parseApiError } from '@/api/client';
import { HealthResponse, CaseItem, MLStatusResponse, DataSourcesResponse } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ErrorState, LoadingState } from '@/components/ui/States';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatusDot } from '@/components/ui/RiskBadge';
import { formatDateTime } from '@/lib/utils';
import { useWebSocket } from '@/context/WebSocketContext';

const StatCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  to?: string;
}> = ({ icon, label, value, sub, color = 'text-cyan-400', to }) => {
  const inner = (
    <div className="flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg bg-[#0d1220] border border-[#1e2e44] flex items-center justify-center ${color} shrink-0`}>
        {icon}
      </div>
      <div>
        <div className="text-2xl font-bold text-slate-100 tabular-nums">{value}</div>
        <div className="text-xs text-slate-500 mt-0.5 uppercase tracking-wider">{label}</div>
        {sub && <div className="text-[11px] text-slate-600 mt-0.5">{sub}</div>}
      </div>
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="block">
        <div className="p-5 bg-[#101624] border border-[#1e293b] rounded-lg hover:border-cyan-800/60 transition-all duration-200 cursor-pointer group">
          {inner}
          <div className="mt-3 text-xs text-slate-600 group-hover:text-cyan-500 flex items-center gap-1 transition-colors">
            View details <ArrowRight className="w-3 h-3" />
          </div>
        </div>
      </Link>
    );
  }

  return (
    <div className="p-5 bg-[#101624] border border-[#1e293b] rounded-lg">
      {inner}
    </div>
  );
};

export const Dashboard: React.FC = () => {
  const { providerStatus, liveTransactions } = useWebSocket();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [mlStatus, setMlStatus] = useState<MLStatusResponse | null>(null);
  const [sources, setSources] = useState<DataSourcesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, c, ml, s] = await Promise.all([
        api.getHealth(),
        api.listCases(),
        api.getMLStatus(),
        api.getDataSources(),
      ]);
      setHealth(h);
      setCases(c);
      setMlStatus(ml);
      setSources(s);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingState message="Initializing GhostTrace intelligence feeds…" />;
  if (error) return <ErrorState title="Backend Unavailable" message={error} onRetry={load} isOffline />;

  const activeCases = cases.filter((c) => c.status !== 'failed');
  const analyzedCases = cases.filter((c) => c.status === 'analyzed');
  const totalTx = cases.reduce((sum, c) => sum + c.tx_count, 0);
  const totalEvidence = cases.reduce((sum, c) => sum + c.evidence_count, 0);

  // Chart data from cases
  const caseChartData = analyzedCases.slice(-8).map((c) => ({
    name: c.case_id.slice(0, 8),
    tx: c.tx_count,
    evidence: c.evidence_count,
  }));

  const availableSources = sources?.data_sources?.filter((s) => s.available) ?? [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight">Investigation Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            GhostTrace Forensic Intelligence Platform •{' '}
            {health ? `v${health.version}` : '—'} •{' '}
            <span className="text-slate-600">{new Date().toLocaleString()}</span>
          </p>
        </div>
        <Link to="/new-case">
          <Button size="sm" icon={<FolderOpen className="w-4 h-4" />}>
            New Case
          </Button>
        </Link>
      </div>

      {/* Real-Time Live Feed Banner */}
      <div className="p-4 rounded-lg bg-[#0e1424] border border-[#1e2e4a] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-950/60 border border-cyan-800/40 flex items-center justify-center text-cyan-400 shrink-0">
            <Activity className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-100">Live Ingestion Engine</span>
              <Badge variant="cyan">Real-Time</Badge>
              {providerStatus?.is_simulated && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/40 text-amber-300 font-mono">
                  SIMULATED
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Provider: <span className="text-cyan-300 font-mono">{providerStatus?.provider_name ?? 'Connecting...'}</span> • Block: <span className="text-slate-200 font-mono">#{providerStatus?.last_processed_block ?? '—'}</span> • Buffer: <span className="text-slate-300 font-mono">{liveTransactions.length} events</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="secondary"
            icon={<TrendingUp className="w-3.5 h-3.5 text-cyan-400" />}
            onClick={async () => {
              try {
                await api.simulateLiveEvent({ amount: 2.5, asset: 'ETH' });
              } catch (e) {
                console.error(e);
              }
            }}
          >
            Simulate Inflow
          </Button>
          <Link to="/graph">
            <Button size="sm" icon={<GitBranch className="w-3.5 h-3.5" />}>
              Live Graph
            </Button>
          </Link>
        </div>
      </div>

      {/* Live Transaction Ticker */}
      {liveTransactions.length > 0 && (
        <Card title="Live Inbound Evidence Feed" subtitle="Transactions processed and indexed in real-time without page reload">
          <div className="space-y-2 max-h-64 overflow-y-auto font-mono text-xs pr-1">
            {liveTransactions.slice(0, 10).map((tx, idx) => (
              <div
                key={tx.event_id || tx.tx_hash || idx}
                className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-2.5 rounded bg-[#090d18] border border-[#1a2336] hover:border-cyan-800/40 transition-colors gap-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping shrink-0" />
                  <span className="font-semibold text-cyan-300">{tx.amount} {tx.asset}</span>
                  <span className="text-slate-500 text-[11px]">from</span>
                  <span className="text-slate-400 truncate max-w-[130px]">{tx.from_address}</span>
                  <span className="text-slate-500 text-[11px]">to</span>
                  <span className="text-slate-400 truncate max-w-[130px]">{tx.to_address}</span>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-slate-500 shrink-0">
                  {tx.block_number && <span>Blk #{tx.block_number}</span>}
                  <span className="text-slate-600 truncate max-w-[90px]">{tx.tx_hash?.slice(0, 10)}…</span>
                  {tx.is_removed ? (
                    <span className="text-red-400 text-[10px] border border-red-900/60 bg-red-950/40 px-1 rounded">REORG REVERTED</span>
                  ) : (
                    <span className="text-emerald-400 text-[10px] border border-emerald-900/60 bg-emerald-950/40 px-1 rounded">INDEXED</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Recent Cases */}
        <div className="xl:col-span-2">
          <Card
            title="Recent Investigations"
            action={
              <Link to="/graph">
                <Button variant="ghost" size="sm" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                  All Cases
                </Button>
              </Link>
            }
          >
            {cases.length === 0 ? (
              <div className="py-10 text-center text-slate-500 text-sm">
                No cases yet. <Link to="/new-case" className="text-cyan-400 hover:underline">Create your first investigation.</Link>
              </div>
            ) : (
              <div className="space-y-2">
                {cases.slice(0, 6).map((c) => (
                  <Link
                    key={c.case_id}
                    to={`/graph?caseId=${c.case_id}`}
                    className="flex items-center justify-between p-3 rounded-lg bg-[#0d1220] border border-[#1a2336] hover:border-cyan-800/40 transition-all duration-150 group"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-200 truncate group-hover:text-cyan-300 transition-colors">
                        {c.case_name}
                      </div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[11px] font-mono text-slate-600">{c.case_id.slice(0, 12)}…</span>
                        <span className="text-[11px] text-slate-600">{c.network}</span>
                        <span className="flex items-center gap-1 text-[11px] text-slate-600">
                          <Clock className="w-3 h-3" />
                          {formatDateTime(c.created_at)}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4 shrink-0">
                      <span className="text-xs text-slate-500">{c.tx_count} tx</span>
                      <Badge
                        variant={
                          c.status === 'analyzed' ? 'emerald'
                          : c.status === 'failed' ? 'crimson'
                          : c.status === 'ingested' ? 'amber'
                          : 'cyan'
                        }
                      >
                        {c.status}
                      </Badge>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Card>

          {/* Cases chart */}
          {caseChartData.length > 0 && (
            <Card title="Transaction Volume by Case" className="mt-4">
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={caseChartData} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#475569' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#475569' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#101624', border: '1px solid #1e293b', borderRadius: 6, fontSize: 12 }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Bar dataKey="tx" radius={[2, 2, 0, 0]} name="Transactions">
                    {caseChartData.map((_, i) => (
                      <Cell key={i} fill="#0e7490" />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* ML Model Status */}
          <Card title="ML Model" subtitle="Active classifier" highlight="cyan">
            {mlStatus ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Status</span>
                  <StatusDot
                    status={mlStatus.model_loaded ? 'online' : 'offline'}
                    label={mlStatus.model_loaded ? 'Loaded' : 'Not Loaded'}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Version</span>
                  <span className="text-xs font-mono text-slate-300">{mlStatus.version ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Algorithm</span>
                  <span className="text-xs text-slate-300">{mlStatus.algorithm ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Features</span>
                  <span className="text-xs text-slate-300">{mlStatus.features_count}</span>
                </div>
                {mlStatus.metrics?.threshold !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">Threshold</span>
                    <span className="text-xs font-mono text-amber-400">{mlStatus.metrics.threshold}</span>
                  </div>
                )}
                {mlStatus.metrics?.f1_score !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">Test F1</span>
                    <span className="text-xs font-mono text-cyan-400">
                      {(mlStatus.metrics.f1_score * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
                <Link to="/benchmark">
                  <Button variant="ghost" size="sm" className="w-full mt-1 text-cyan-400" icon={<Activity className="w-3.5 h-3.5" />}>
                    Full Metrics
                  </Button>
                </Link>
              </div>
            ) : (
              <Skeleton className="h-4 w-full mt-2" count={4} />
            )}
          </Card>

          {/* TraceChain Status */}
          <Card title="TraceChain Ledger" subtitle="Cryptographic audit log">
            {health ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Block Height</span>
                  <span className="text-xs font-mono text-slate-200">{health.tracechain.block_height}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Integrity</span>
                  <StatusDot
                    status={health.tracechain.integrity_valid ? 'online' : 'offline'}
                    label={health.tracechain.integrity_valid ? 'Valid' : 'Compromised'}
                  />
                </div>
                <div className="text-[10px] text-slate-600 pt-1 border-t border-[#1a2336]">
                  {health.tracechain.status}
                </div>
                <Link to="/audit">
                  <Button variant="ghost" size="sm" className="w-full text-emerald-400">
                    Verify Chain
                  </Button>
                </Link>
              </div>
            ) : <Skeleton className="h-4 w-full" count={3} />}
          </Card>

          {/* Data Sources */}
          <Card title="Intelligence Sources">
            <div className="space-y-2">
              {sources?.data_sources.map((src) => (
                <div key={src.id} className="flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="text-xs text-slate-300 truncate">{src.name.split(' ')[0]}</div>
                    <div className="text-[10px] text-slate-600 font-mono">{src.network}</div>
                  </div>
                  <StatusDot status={src.available ? 'online' : 'offline'} label={src.available ? 'Ready' : 'Unavail.'} />
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="p-3 rounded-lg border border-amber-900/40 bg-amber-950/20 text-[11px] text-amber-300/80">
        <span className="font-semibold">⚠ Investigative Disclaimer:</span> All findings are probabilistic leads derived from graph analytics and ML inference. No lead constitutes legal proof or identity attribution. Consult qualified forensic analysts before taking any legal action.
      </div>
    </div>
  );
};
