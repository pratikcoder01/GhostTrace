import React, { useState, useEffect, useCallback } from 'react';
import { TrendingDown, Info, AlertTriangle, RefreshCw, Radio } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { api, parseApiError } from '@/api/client';
import { CashoutForecastResponse, CaseItem, WebSocketLiveEvent } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { useWebSocket } from '@/context/WebSocketContext';

const RISK_COLORS: Record<string, string> = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#eab308',
  Low: '#10b981',
};

export const CashoutForecast: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [forecast, setForecast] = useState<CashoutForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastLiveUpdate, setLastLiveUpdate] = useState<string | null>(null);

  const { registerListener } = useWebSocket();

  // Load cases list
  useEffect(() => {
    api.listCases().then((cList) => {
      setCases(cList);
      if (cList.length > 0 && !selectedCaseId) {
        setSelectedCaseId(cList[0].case_id);
      }
    }).catch((err) => {
      setError(parseApiError(err));
    });
  }, []);

  const loadForecast = useCallback(async (caseId: string) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCashoutForecast(caseId);
      setForecast(data);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadForecast(selectedCaseId);
    }
  }, [selectedCaseId, loadForecast]);

  // Subscribe to live forecast updates via WebSocket
  useEffect(() => {
    const cleanup = registerListener('forecast.updated', (event: WebSocketLiveEvent) => {
      if (event.case_id === selectedCaseId || !event.case_id) {
        setLastLiveUpdate(new Date().toLocaleTimeString());
        loadForecast(selectedCaseId);
      }
    });
    return cleanup;
  }, [registerListener, selectedCaseId, loadForecast]);

  const peakWindow = forecast?.forecast_by_day
    ? [...forecast.forecast_by_day].sort((a, b) => b.probability - a.probability)[0]?.day || 'T+3'
    : 'T+3';

  const highestProb = forecast?.forecast_by_day
    ? Math.max(0, ...forecast.forecast_by_day.map((d) => d.probability))
    : 0;

  return (
    <div className="space-y-6">
      {/* Header with Case Selector */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <TrendingDown className="w-3.5 h-3.5" />
            <span>TEMPORAL DISPERSION & LIQUIDATION MODEL</span>
          </div>
          <h1 className="text-xl font-bold text-slate-100">Cash-out Liquidation Forecast</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Projected liquidation timing and route probability analysis computed from on-chain temporal burst patterns.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastLiveUpdate && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-cyan-950/40 border border-cyan-800 text-[11px] font-mono text-cyan-300">
              <Radio className="w-3 h-3 text-cyan-400 animate-pulse" />
              <span>Live: {lastLiveUpdate}</span>
            </div>
          )}
          <label className="text-xs text-slate-400">Case:</label>
          <select
            value={selectedCaseId}
            onChange={(e) => setSelectedCaseId(e.target.value)}
            className="bg-[#0c1c2f] border border-[#263649] text-xs font-mono text-slate-200 rounded px-3 py-1.5 focus:border-cyan-500 outline-none"
          >
            {cases.map((c) => (
              <option key={c.case_id} value={c.case_id}>
                {c.case_name} ({c.case_id.slice(0, 10)})
              </option>
            ))}
          </select>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => loadForecast(selectedCaseId)}
            disabled={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Critical warning */}
      <div className="p-3.5 rounded-lg border border-amber-900/60 bg-amber-950/25 flex items-start gap-3 text-xs text-amber-200">
        <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
        <div>
          <strong className="text-amber-300">PROBABILISTIC WINDOW ESTIMATES (NO COUNTDOWN TIMERS):</strong> Cash-out forecasting
          cannot provide deterministic ETAs. These curves are probabilistic distribution estimates derived from observed
          temporal transfer intervals and exit gate interactions — not individual tracking or surveillance.
        </div>
      </div>

      {loading && <LoadingState message="Calculating temporal liquidation forecast…" />}
      {error && <ErrorState title="Forecast Calculation Failed" message={error} onRetry={() => loadForecast(selectedCaseId)} />}

      {!loading && !error && forecast && (
        <div className="space-y-6">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg">
              <div className="text-2xl font-bold font-mono text-cyan-400">
                {forecast.total_initial_compromised.toLocaleString()} ETH
              </div>
              <div className="text-xs text-slate-400 mt-1">Traced Outflow</div>
            </div>

            <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg">
              <div className="text-2xl font-bold font-mono text-red-400">
                {peakWindow}
              </div>
              <div className="text-xs text-slate-400 mt-1">Peak Dispersion Window</div>
            </div>

            <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg">
              <div className="text-2xl font-bold font-mono text-amber-400">
                {highestProb}%
              </div>
              <div className="text-xs text-slate-400 mt-1">Peak Probability</div>
            </div>

            <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg">
              <div className="text-2xl font-bold font-mono text-emerald-400">
                {forecast.routes.length} Active Routes
              </div>
              <div className="text-xs text-slate-400 mt-1">Exit Routes Identified</div>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {/* Volume forecast chart */}
            <Card title="Projected Liquidation Volume by Day" subtitle="Computed temporal density across multi-day horizon">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={forecast.forecast_by_day} margin={{ top: 8, right: 8, bottom: 4, left: -15 }}>
                  <defs>
                    <linearGradient id="forecastVolGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1b2b3e" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#859397' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#859397' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0c1c2f', border: '1px solid #263649', borderRadius: 6, fontSize: 12 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="volume"
                    stroke="#22d3ee"
                    fill="url(#forecastVolGrad)"
                    strokeWidth={2}
                    name="Volume (ETH)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            {/* Probability forecast chart */}
            <Card title="Cash-out Probability % by Day" subtitle="Calculated exit likelihood distribution">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={forecast.forecast_by_day} margin={{ top: 8, right: 8, bottom: 4, left: -15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1b2b3e" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#859397' }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#859397' }} unit="%" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0c1c2f', border: '1px solid #263649', borderRadius: 6, fontSize: 12 }}
                    formatter={(v: any) => [`${v as number}%`, 'Probability']}
                  />
                  <Bar dataKey="probability" radius={[3, 3, 0, 0]} name="Probability">
                    {forecast.forecast_by_day.map((d, i) => (
                      <Cell
                        key={i}
                        fill={d.probability > 50 ? '#ffb4ab' : d.probability > 25 ? '#ffd6a7' : '#22d3ee'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Identified Cash-out Routes */}
          <Card title="Identified Dissipation Routes" subtitle="Graph paths identified during forensic cluster traversal">
            <div className="space-y-3">
              {forecast.routes.map((route) => (
                <div
                  key={route.route}
                  className="flex items-center gap-4 p-3.5 bg-[#0c1c2f] border border-[#1b2b3e] rounded-lg"
                >
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-slate-200">{route.route}</div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Estimated Volume: <span className="font-mono text-cyan-300 font-bold">{route.volume.toLocaleString()} ETH</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-28 bg-[#102033] rounded-full overflow-hidden border border-[#263649]">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(100, (route.volume / (forecast.total_initial_compromised || 1)) * 100)}%`,
                          backgroundColor: RISK_COLORS[route.risk] || '#22d3ee',
                        }}
                      />
                    </div>
                    <Badge variant={route.risk === 'Critical' ? 'crimson' : route.risk === 'High' ? 'amber' : 'slate'} size="sm">
                      {route.risk}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
