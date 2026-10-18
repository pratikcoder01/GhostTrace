import React, { useEffect, useState, useCallback } from 'react';
import { FileText, Download, RefreshCw, AlertTriangle } from 'lucide-react';
import { api, parseApiError } from '@/api/client';
import { InvestigationReportResponse, CaseItem } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { ErrorState, EmptyState, LoadingState } from '@/components/ui/States';
import { formatDateTime, downloadJsonFile } from '@/lib/utils';

export const Reports: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [report, setReport] = useState<InvestigationReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.listCases().then(setCases).catch(() => {}); }, []);

  const loadReport = useCallback(async (caseId: string) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const r = await api.getCaseReport(caseId);
      setReport(r);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (selectedCaseId) loadReport(selectedCaseId); }, [selectedCaseId, loadReport]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Forensic Reports</h1>
          <p className="text-xs text-slate-500 mt-0.5">Full cryptographically-verified investigation reports with timeline and audit logs.</p>
        </div>
        <div className="flex gap-2">
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
          {report && (
            <Button
              size="sm"
              variant="secondary"
              icon={<Download className="w-4 h-4" />}
              onClick={() => downloadJsonFile(`ghosttrace_report_${report.case_id.slice(0,8)}.json`, report)}
            >
              Export JSON
            </Button>
          )}
        </div>
      </div>

      {!selectedCaseId && <EmptyState icon={<FileText className="w-7 h-7" />} title="No Case Selected" message="Select a case to generate its full forensic report." />}
      {selectedCaseId && loading && <LoadingState message="Generating forensic report…" />}
      {selectedCaseId && !loading && error && <ErrorState title="Report Generation Failed" message={error} onRetry={() => loadReport(selectedCaseId)} />}

      {report && !loading && (
        <div className="space-y-5">
          {/* Header */}
          <Card highlight="cyan">
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-white">{report.case_name}</h2>
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                    <span className="font-mono">{report.case_id}</span>
                    <span>{report.network}</span>
                    <Badge variant={report.status === 'analyzed' ? 'emerald' : 'amber'}>{report.status}</Badge>
                  </div>
                </div>
                <div className="text-right text-xs text-slate-500 shrink-0">
                  <div>Created: {formatDateTime(report.created_at)}</div>
                  <div>Generated: {formatDateTime(report.generated_at)}</div>
                </div>
              </div>
              <div className="border-t border-[#1a2336] pt-3">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Executive Summary</div>
                <p className="text-sm text-slate-300 leading-relaxed">{report.executive_summary}</p>
              </div>
            </div>
          </Card>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Total Transactions', value: report.transaction_statistics.total_tx_count ?? 0 },
              { label: 'Unique Senders', value: report.transaction_statistics.unique_senders ?? 0 },
              { label: 'Unique Receivers', value: report.transaction_statistics.unique_receivers ?? 0 },
              { label: 'Temporal Bursts', value: report.transaction_statistics.burst_count ?? 0 },
            ].map((stat) => (
              <div key={stat.label} className="p-4 bg-[#101624] border border-[#1e293b] rounded-lg text-center">
                <div className="text-2xl font-bold text-slate-100 tabular-nums">{Number(stat.value).toLocaleString()}</div>
                <div className="text-xs text-slate-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {/* Leads */}
            <Card title={`Ranked Leads (${report.ranked_leads.length})`}>
              <div className="space-y-2">
                {report.ranked_leads.slice(0, 8).map((lead, idx) => (
                  <div key={lead.lead_id} className="flex items-center gap-3 py-2 border-b border-[#1a2336] last:border-0">
                    <span className="text-xs font-mono text-slate-600 w-5 text-right">#{idx + 1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-mono text-xs text-cyan-400 truncate">{lead.address}</div>
                      <div className="text-[11px] text-slate-600 truncate">{lead.summary}</div>
                    </div>
                    <RiskBadge level={lead.risk_level} score={lead.priority_score} />
                  </div>
                ))}
                {report.ranked_leads.length === 0 && (
                  <div className="text-sm text-slate-600 text-center py-4">No leads generated</div>
                )}
              </div>
            </Card>

            {/* Timeline */}
            <Card title={`Timeline Events (${report.timeline.length})`} bodyClassName="max-h-80 overflow-y-auto">
              <div className="space-y-3">
                {report.timeline.map((ev, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <div className="flex flex-col items-center gap-1 shrink-0">
                      <div className="w-2 h-2 rounded-full bg-cyan-700 mt-1.5" />
                      {idx < report.timeline.length - 1 && <div className="w-px flex-1 bg-[#1a2336]" />}
                    </div>
                    <div className="pb-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] text-slate-500">{formatDateTime(ev.timestamp)}</span>
                        <Badge variant="slate" size="sm">{ev.event_type}</Badge>
                        {ev.flags.map((f) => <Badge key={f} variant="amber" size="sm">{f}</Badge>)}
                      </div>
                      <div className="text-xs text-slate-300 mt-0.5 leading-relaxed">{ev.description}</div>
                    </div>
                  </div>
                ))}
                {report.timeline.length === 0 && <div className="text-sm text-slate-600 text-center py-4">No timeline events</div>}
              </div>
            </Card>
          </div>

          {/* TraceChain audit */}
          <Card title="TraceChain Audit" highlight={report.tracechain_audit.is_valid ? 'none' : 'crimson'}>
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${report.tracechain_audit.is_valid ? 'bg-emerald-400' : 'bg-red-400'}`} />
                <span className={`text-sm font-semibold ${report.tracechain_audit.is_valid ? 'text-emerald-300' : 'text-red-300'}`}>
                  {report.tracechain_audit.is_valid ? 'Chain Valid' : 'Chain Compromised'}
                </span>
              </div>
              <span className="text-xs text-slate-500">{report.tracechain_audit.verification_status}</span>
              <Badge variant="cyan">{report.tracechain_audit.total_blocks} blocks</Badge>
            </div>
          </Card>

          {/* ML Assessment */}
          {report.ml_assessment && (
            <Card title="ML Assessment" subtitle="AI-assisted classification context">
              <div className="grid grid-cols-2 gap-3 text-xs">
                {Object.entries(report.ml_assessment).map(([k, v]) => (
                  <div key={k} className="flex flex-col">
                    <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}</span>
                    <span className="text-slate-300 mt-0.5 font-mono">{String(v)}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Disclaimer */}
          <Card bodyClassName="bg-amber-950/20 border-amber-900/40">
            <div className="flex items-start gap-2 text-xs text-amber-300">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <p className="leading-relaxed">{report.limitations_and_disclaimer}</p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
