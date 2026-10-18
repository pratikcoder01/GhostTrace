import React, { useEffect, useState, useCallback } from 'react';
import { AlertTriangle, ChevronDown, ChevronRight, Info } from 'lucide-react';
import { api, parseApiError } from '@/api/client';
import { AnalysisLead, CaseItem, WebSocketLiveEvent } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { ErrorState, EmptyState, LoadingState } from '@/components/ui/States';
import { truncateAddress } from '@/lib/utils';
import { useToast } from '@/components/ui/ToastContext';
import { useWebSocket } from '@/context/WebSocketContext';

export const Leads: React.FC = () => {
  const { showToast } = useToast();
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [leads, setLeads] = useState<AnalysisLead[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { registerListener, subscribeToCase, unsubscribeFromCase } = useWebSocket();

  useEffect(() => { api.listCases().then(setCases).catch(() => {}); }, []);

  const loadLeads = useCallback(async (caseId: string) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.getCaseLeads(caseId);
      setLeads(result.leads ?? []);
    } catch {
      try {
        const analyzeRes = await api.analyzeCase(caseId);
        setLeads(analyzeRes.ranked_leads ?? []);
      } catch (innerErr) {
        setError(parseApiError(innerErr));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadLeads(selectedCaseId);
      subscribeToCase(selectedCaseId);

      const cleanup = registerListener('lead.created', (event: WebSocketLiveEvent) => {
        if (event.case_id === selectedCaseId || !event.case_id) {
          showToast({
            type: 'info',
            title: 'New Forensic Lead',
            message: 'A new suspect wallet lead was identified by the forensic engine.',
          });
          loadLeads(selectedCaseId);
        }
      });

      return () => {
        unsubscribeFromCase(selectedCaseId);
        cleanup();
      };
    }
  }, [selectedCaseId, loadLeads, subscribeToCase, unsubscribeFromCase, registerListener, showToast]);

  const toggleExpand = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Investigative Leads</h1>
          <p className="text-xs text-slate-500 mt-0.5">Ranked high-confidence forensic leads from graph analytics. Lead ≠ Proof.</p>
        </div>
        <select
          value={selectedCaseId}
          onChange={(e) => setSelectedCaseId(e.target.value)}
          className="bg-[#0d1220] border border-[#1e293b] text-sm text-slate-300 rounded-md px-3 py-1.5 focus:border-cyan-700 outline-none min-w-[240px]"
        >
          <option value="">— Select a Case —</option>
          {cases.map((c) => (
            <option key={c.case_id} value={c.case_id}>{c.case_name}</option>
          ))}
        </select>
      </div>

      {/* Lead disclaimer */}
      <div className="p-3 rounded-lg border border-amber-900/40 bg-amber-950/20 flex items-start gap-2 text-xs text-amber-300">
        <Info className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
        <span>
          <strong>LEAD, NOT PROOF:</strong> All leads are probabilistic and generated from graph heuristics and ML inference. Leads do not constitute identification of individuals, attribution of funds, or admissible legal evidence. Always corroborate with independent forensic investigation.
        </span>
      </div>

      {!selectedCaseId && <EmptyState icon={<AlertTriangle className="w-7 h-7" />} title="No Case Selected" message="Select a case to load ranked forensic leads." />}
      {selectedCaseId && loading && <LoadingState message="Running graph analysis and ranking leads…" />}
      {selectedCaseId && !loading && error && <ErrorState title="Analysis Failed" message={error} onRetry={() => loadLeads(selectedCaseId)} />}
      {selectedCaseId && !loading && !error && leads.length === 0 && (
        <EmptyState icon={<AlertTriangle className="w-7 h-7" />} title="No Leads Generated" message="Run analysis or ensure the case has ingested transactions." />
      )}

      {!loading && !error && leads.length > 0 && (
        <div className="space-y-3">
          {leads.map((lead, idx) => {
            const isOpen = expanded.has(lead.lead_id);
            return (
              <div
                key={lead.lead_id}
                className="bg-[#101624] border border-[#1e293b] rounded-lg overflow-hidden"
              >
                <button
                  className="w-full flex items-center gap-4 px-5 py-3.5 text-left hover:bg-[#141d2e] transition-colors"
                  onClick={() => toggleExpand(lead.lead_id)}
                  aria-expanded={isOpen}
                >
                  <span className="text-xs font-mono text-slate-600 w-5 text-right shrink-0">#{idx + 1}</span>
                  {isOpen ? <ChevronDown className="w-4 h-4 text-slate-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-slate-500 shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm text-cyan-400 truncate">{lead.address}</div>
                    <div className="text-xs text-slate-500 mt-0.5 truncate">{lead.summary}</div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs font-mono text-slate-400">Score {lead.priority_score.toFixed(1)}</span>
                    <RiskBadge level={lead.risk_level} />
                  </div>
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 border-t border-[#1a2336] pt-4 space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs text-slate-500 mb-1.5 uppercase tracking-wider">Full Address</div>
                        <div className="font-mono text-xs text-cyan-400 break-all bg-[#0d1220] px-2 py-1.5 rounded border border-[#1a2336]">{lead.address}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 mb-1.5 uppercase tracking-wider">Provenance</div>
                        <div className="text-xs text-slate-300 bg-[#0d1220] px-2 py-1.5 rounded border border-[#1a2336]">{lead.provenance}</div>
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Reason Codes</div>
                      <div className="flex flex-wrap gap-2">
                        {lead.reason_codes.map((r) => (
                          <Badge key={r} variant="amber" size="sm">{r}</Badge>
                        ))}
                      </div>
                    </div>

                    {lead.supporting_tx_ids.length > 0 && (
                      <div>
                        <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Supporting Transactions ({lead.supporting_tx_ids.length})</div>
                        <div className="flex flex-wrap gap-1.5">
                          {lead.supporting_tx_ids.slice(0, 12).map((tx) => (
                            <span key={tx} className="font-mono text-[10px] text-slate-400 bg-[#0d1220] px-1.5 py-0.5 rounded border border-[#1a2336]">
                              {truncateAddress(tx, 8, 4)}
                            </span>
                          ))}
                          {lead.supporting_tx_ids.length > 12 && (
                            <span className="text-[10px] text-slate-600">+{lead.supporting_tx_ids.length - 12} more</span>
                          )}
                        </div>
                      </div>
                    )}

                    {lead.evidence_ids.length > 0 && (
                      <div>
                        <div className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Linked Evidence IDs</div>
                        <div className="text-xs text-slate-400">{lead.evidence_ids.join(', ')}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
