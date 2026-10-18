import React, { useState, useEffect, useCallback } from 'react';
import { Layers, AlertTriangle, Info, TrendingDown, ArrowRight, ShieldAlert, RefreshCw } from 'lucide-react';
import { api, parseApiError } from '@/api/client';
import { ExposureResponse, CaseItem } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState, ErrorState } from '@/components/ui/States';

export const Exposure: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [data, setData] = useState<ExposureResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load cases
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

  const loadExposure = useCallback(async (caseId: string) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCaseExposure(caseId);
      setData(res);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadExposure(selectedCaseId);
    }
  }, [selectedCaseId, loadExposure]);

  return (
    <div className="space-y-6">
      {/* Header with Case Selector */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Layers className="w-3.5 h-3.5" />
            <span>FORENSIC EXPOSURE ANALYSIS</span>
          </div>
          <h1 className="text-xl font-bold text-slate-100">Exposure & Exit Projection</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Traced on-chain dissipation paths, candidate liquidation exit gates, and bounded exposure boundaries.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-400">Investigation Case:</label>
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
            onClick={() => loadExposure(selectedCaseId)}
            disabled={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Critical Double-Counting Caveat */}
      <div className="p-3.5 rounded-lg border border-amber-900/60 bg-amber-950/25 flex items-start gap-3 text-xs text-amber-200">
        <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-amber-300">DOUBLE-COUNTING AUDIT WARNING:</span>
          <p className="text-amber-200/90 leading-relaxed">
            Funds identified at downstream exit gateways represent the <em>same</em> asset units observed across intermediate hops.
            Never aggregate or sum multi-hop amounts to avoid artificial volume inflation.
          </p>
        </div>
      </div>

      {loading && <LoadingState message="Computing multi-hop exposure metrics…" />}
      {error && <ErrorState title="Exposure Calculation Failed" message={error} onRetry={() => loadExposure(selectedCaseId)} />}

      {!loading && !error && data && (
        <div className="space-y-6">
          {/* KPI Stat Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg">
              <div className="text-xs text-slate-400 mb-1">Observed Source Outflow</div>
              <div className="text-2xl font-bold font-mono text-cyan-400">
                {data.observedSourceOutflow.toLocaleString()} {data.asset}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Traced from designated seed wallets</div>
            </div>

            <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg">
              <div className="text-xs text-slate-400 mb-1">Notional Valuation</div>
              <div className="text-2xl font-bold font-mono text-emerald-400">
                ${data.observedSourceOutflowUSD.toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Benchmark USD equivalent at timestamp</div>
            </div>

            <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg">
              <div className="text-xs text-slate-400 mb-1">Candidate Exit Amount</div>
              <div className="text-2xl font-bold font-mono text-amber-400">
                {data.candidateExitAmount ? `${data.candidateExitAmount.toLocaleString()} ${data.asset}` : '—'}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Observed at terminal exit gates</div>
            </div>
          </div>

          {/* Candidate Exit Gateways */}
          <Card title="Candidate Exit Gateways" subtitle="Identified centralized exchanges, mixer contracts, or OTC liquidation points">
            <div className="space-y-3">
              {data.candidateExits.map((exit, idx) => (
                <div
                  key={exit.walletId || idx}
                  className="flex items-center justify-between p-3.5 bg-[#0c1c2f] border border-[#1b2b3e] rounded-lg"
                >
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-slate-200">{exit.label}</div>
                    <div className="text-xs font-mono text-cyan-400">{exit.address}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold font-mono text-amber-300">
                      {exit.observedAmount.toLocaleString()} {data.asset}
                    </div>
                    <Badge variant="amber" size="sm" className="mt-1">
                      CANDIDATE_EXIT
                    </Badge>
                  </div>
                </div>
              ))}

              {data.candidateExits.length === 0 && (
                <div className="text-center text-slate-500 text-sm py-6">
                  No candidate exit gateways detected in current trace horizon.
                </div>
              )}
            </div>
          </Card>

          {/* Path Summaries */}
          <Card title="Traced Flow Paths" subtitle="Sequential directed transfer routes from seed compromise to candidate endpoints">
            <div className="space-y-2.5">
              {data.pathSummary.map((ps, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-[#0c1c2f] border border-[#1b2b3e] rounded-lg flex items-center justify-between flex-wrap gap-2 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant={ps.type === 'CANDIDATE_PRIMARY' ? 'cyan' : 'slate'} size="sm">
                      {ps.type}
                    </Badge>
                    <span className="font-mono text-slate-300 break-all">{ps.path}</span>
                  </div>
                  <div className="font-mono font-semibold text-cyan-300 shrink-0">
                    {ps.amount.toLocaleString()} {data.asset}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Projection Methodology Notice */}
          <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg space-y-2 text-xs text-slate-400">
            <div className="flex items-center gap-2 text-cyan-400 font-semibold">
              <Info className="w-4 h-4" />
              <span>FORENSIC METHODOLOGY & PROJECTION BOUNDS</span>
            </div>
            <p className="leading-relaxed">
              {data.projectionNote}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
