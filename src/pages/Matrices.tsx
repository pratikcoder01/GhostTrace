import React, { useState, useEffect, useCallback } from 'react';
import { Grid3X3, Clock, BarChart3, Wallet, Info, RefreshCw, ArrowRight, Shield } from 'lucide-react';
import { api, parseApiError } from '@/api/client';
import { MatricesResponse, CaseItem, WalletItem } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState, ErrorState } from '@/components/ui/States';

function truncAddr(addr: string): string {
  if (!addr) return '';
  if (addr.length <= 12) return addr;
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

export const Matrices: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [data, setData] = useState<MatricesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'flow' | 'activity' | 'features' | 'wallets'>('flow');
  const [selectedCell, setSelectedCell] = useState<{ from: string; to: string; val: number } | null>(null);

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

  const loadMatrices = useCallback(async (caseId: string) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCaseMatrices(caseId);
      setData(res);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadMatrices(selectedCaseId);
    }
  }, [selectedCaseId, loadMatrices]);

  const maxFlow = data
    ? Math.max(1, ...Object.values(data.flowMatrix).flatMap((row) => Object.values(row)))
    : 1;

  const maxActivity = data
    ? Math.max(
        1,
        ...data.walletIds.flatMap((wid) => data.bins.map((b) => data.activityMatrix[wid]?.[b] || 0))
      )
    : 1;

  return (
    <div className="space-y-6">
      {/* Header & Case Selector */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Grid3X3 className="w-3.5 h-3.5" />
            <span>GRAPH ADJACENCY & LEDGER TENSORS</span>
          </div>
          <h1 className="text-xl font-bold text-slate-100">Matrices & Forensic Patterns</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Wallet-to-wallet transfer tensor, temporal dispersion heatmap, and structural topology features.
          </p>
        </div>

        <div className="flex items-center gap-3">
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
            onClick={() => loadMatrices(selectedCaseId)}
            disabled={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#263649] gap-6 text-sm">
        <button
          onClick={() => setActiveTab('flow')}
          className={`pb-3 font-medium flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'flow'
              ? 'border-cyan-400 text-cyan-300'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Grid3X3 className="w-4 h-4" />
          <span>Flow Matrix (A)</span>
        </button>

        <button
          onClick={() => setActiveTab('activity')}
          className={`pb-3 font-medium flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'activity'
              ? 'border-cyan-400 text-cyan-300'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Activity Dispersion (T)</span>
        </button>

        <button
          onClick={() => setActiveTab('features')}
          className={`pb-3 font-medium flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'features'
              ? 'border-cyan-400 text-cyan-300'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Feature Tensors (F)</span>
        </button>

        <button
          onClick={() => setActiveTab('wallets')}
          className={`pb-3 font-medium flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'wallets'
              ? 'border-cyan-400 text-cyan-300'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Wallet className="w-4 h-4" />
          <span>Wallets & Nodes ({data?.wallets.length || 0})</span>
        </button>
      </div>

      {loading && <LoadingState message="Computing matrix tensors from graph..." />}
      {error && <ErrorState title="Matrix Calculation Failed" message={error} onRetry={() => loadMatrices(selectedCaseId)} />}

      {!loading && !error && data && (
        <div>
          {/* TAB 1: FLOW MATRIX */}
          {activeTab === 'flow' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2 text-xs text-slate-400">
                <p>
                  Each cell displays observed transfer amount sent from the row address to the column address.
                </p>
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span>0 Flow</span>
                  <div className="w-16 h-2 rounded bg-gradient-to-r from-transparent via-cyan-900/60 to-cyan-400" />
                  <span>Max Flow ({maxFlow.toFixed(1)})</span>
                </div>
              </div>

              {selectedCell && (
                <div className="p-3 bg-cyan-950/30 border border-cyan-800/50 rounded-lg flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-cyan-300">{truncAddr(selectedCell.from)}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-cyan-300">{truncAddr(selectedCell.to)}</span>
                    <span className="text-slate-400">:</span>
                    <span className="text-slate-100 font-bold">{selectedCell.val.toLocaleString()} ETH</span>
                  </div>
                  <button
                    onClick={() => setSelectedCell(null)}
                    className="text-slate-400 hover:text-slate-200 text-xs font-mono"
                  >
                    Clear
                  </button>
                </div>
              )}

              <div className="overflow-x-auto rounded-lg border border-[#263649] bg-[#0c1c2f]">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[#263649] bg-[#102033] text-slate-400 text-[11px]">
                      <th className="p-2.5 sticky left-0 bg-[#102033] z-10">FROM \ TO</th>
                      {data.walletIds.map((wid) => (
                        <th key={wid} className="p-2 text-center truncate max-w-[80px]" title={wid}>
                          {truncAddr(wid)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.walletIds.map((fromId) => (
                      <tr key={fromId} className="border-b border-[#1b2b3e]/60 hover:bg-[#142336]/40">
                        <td className="p-2.5 sticky left-0 bg-[#0c1c2f] z-10 text-slate-300 font-medium">
                          {truncAddr(fromId)}
                        </td>
                        {data.walletIds.map((toId) => {
                          const val = data.flowMatrix[fromId]?.[toId] || 0;
                          const intensity = val > 0 ? 0.15 + (val / maxFlow) * 0.75 : 0;
                          return (
                            <td
                              key={toId}
                              onClick={val > 0 ? () => setSelectedCell({ from: fromId, to: toId, val }) : undefined}
                              className={`p-2 text-center tabular-nums transition-colors ${
                                val > 0 ? 'cursor-pointer hover:ring-1 hover:ring-cyan-400 font-bold' : 'text-slate-700'
                              }`}
                              style={{
                                backgroundColor: val > 0 ? `rgba(34, 211, 238, ${intensity})` : 'transparent',
                                color: val > 0 ? '#d3e4fd' : '#475569',
                              }}
                              title={val > 0 ? `${fromId} → ${toId}: ${val} ETH` : undefined}
                            >
                              {val > 0 ? val.toFixed(1) : '—'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: ACTIVITY DISPERSION */}
          {activeTab === 'activity' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2 text-xs text-slate-400">
                <p>
                  Transaction event density per wallet across sequential time intervals.
                </p>
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span>Low</span>
                  <div className="w-16 h-2 rounded bg-gradient-to-r from-transparent via-purple-900/60 to-purple-400" />
                  <span>High Activity</span>
                </div>
              </div>

              <div className="overflow-x-auto rounded-lg border border-[#263649] bg-[#0c1c2f]">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[#263649] bg-[#102033] text-slate-400 text-[11px]">
                      <th className="p-2.5 sticky left-0 bg-[#102033] z-10">WALLET ADDRESS</th>
                      {data.bins.map((bin) => (
                        <th key={bin} className="p-2 text-center text-slate-300">
                          {bin}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.walletIds.map((wid) => (
                      <tr key={wid} className="border-b border-[#1b2b3e]/60 hover:bg-[#142336]/40">
                        <td className="p-2.5 sticky left-0 bg-[#0c1c2f] z-10 text-slate-300 font-medium">
                          {truncAddr(wid)}
                        </td>
                        {data.bins.map((bin) => {
                          const count = data.activityMatrix[wid]?.[bin] || 0;
                          const intensity = count > 0 ? 0.2 + (count / maxActivity) * 0.7 : 0;
                          return (
                            <td
                              key={bin}
                              className="p-2 text-center tabular-nums font-semibold"
                              style={{
                                backgroundColor: count > 0 ? `rgba(168, 85, 247, ${intensity})` : 'transparent',
                                color: count > 0 ? '#f3e8ff' : '#475569',
                              }}
                            >
                              {count > 0 ? count : '—'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: FEATURE TENSORS */}
          {activeTab === 'features' && (
            <div className="space-y-4">
              <p className="text-xs text-slate-400">
                Network topology metrics computed per node, used as structural features for illicit transaction classification.
              </p>

              <div className="overflow-x-auto rounded-lg border border-[#263649] bg-[#0c1c2f]">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[#263649] bg-[#102033] text-slate-400 text-[11px]">
                      <th className="p-2.5">WALLET ADDRESS</th>
                      <th className="p-2 text-center">FAN-IN (IN-DEGREE)</th>
                      <th className="p-2 text-center">FAN-OUT (OUT-DEGREE)</th>
                      <th className="p-2 text-center">TOTAL OUTFLOW</th>
                      <th className="p-2 text-center">MEAN TRANSFER</th>
                      <th className="p-2 text-center">HOP DEPTH</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.walletIds.map((wid) => {
                      const feat = data.featureMatrix[wid];
                      if (!feat) return null;
                      return (
                        <tr key={wid} className="border-b border-[#1b2b3e]/60 hover:bg-[#142336]/40">
                          <td className="p-2.5 text-cyan-300 font-semibold">{wid}</td>
                          <td className="p-2 text-center text-slate-200">{feat.fanIn}</td>
                          <td className="p-2 text-center text-slate-200">{feat.fanOut}</td>
                          <td className="p-2 text-center text-cyan-400 font-bold">{feat.totalOut.toLocaleString()} ETH</td>
                          <td className="p-2 text-center text-slate-300">{feat.meanTransferAmt.toLocaleString()} ETH</td>
                          <td className="p-2 text-center">
                            <Badge variant={feat.hopDepth === 0 ? 'crimson' : feat.hopDepth === 1 ? 'amber' : 'slate'} size="sm">
                              Depth {feat.hopDepth}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: WALLETS */}
          {activeTab === 'wallets' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.wallets.map((w) => (
                <Card
                  key={w.id}
                  title={
                    <div className="flex items-center gap-2">
                      <Wallet className="w-4 h-4 text-cyan-400" />
                      <span className="font-mono text-xs text-slate-200 truncate">{truncAddr(w.address)}</span>
                    </div>
                  }
                  action={
                    <Badge variant={w.risk_level === 'Critical' ? 'crimson' : w.risk_level === 'High' ? 'amber' : 'slate'} size="sm">
                      {w.risk_level || 'Low'}
                    </Badge>
                  }
                  bodyClassName="space-y-2.5 text-xs"
                >
                  <div className="text-[11px] text-slate-400 font-medium">{w.label}</div>
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#1b2b3e]">
                    <div>
                      <div className="text-[10px] text-slate-500">Total Inflow</div>
                      <div className="font-mono text-emerald-400 font-semibold">{w.inflow?.toLocaleString()} ETH</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-500">Total Outflow</div>
                      <div className="font-mono text-cyan-400 font-semibold">{w.outflow?.toLocaleString()} ETH</div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-[#1b2b3e]">
                    <span>Category: <strong className="text-slate-300">{w.category}</strong></span>
                    <span>Txs: <strong className="text-slate-300">{w.tx_count}</strong></span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
