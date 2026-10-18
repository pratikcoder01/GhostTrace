import React, { useEffect, useState, useCallback } from 'react';
import { Search, ExternalLink, AlertTriangle, Shield } from 'lucide-react';
import { api, parseApiError } from '@/api/client';
import { EvidenceItem, CaseItem } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ErrorState, EmptyState, LoadingState } from '@/components/ui/States';
import { formatDateTime } from '@/lib/utils';

const CATEGORY_VARIANTS: Record<string, 'crimson' | 'amber' | 'cyan' | 'purple' | 'emerald' | 'slate'> = {
  scam_wallet: 'crimson',
  phishing: 'crimson',
  ransomware: 'crimson',
  darknet_market: 'amber',
  mixer: 'amber',
  exchange: 'cyan',
  threat_intel: 'purple',
  osint: 'slate',
};

export const OSINT: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');

  useEffect(() => { api.listCases().then(setCases).catch(() => {}); }, []);

  const loadEvidence = useCallback(async (caseId: string) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCaseEvidence(caseId);
      setEvidence(data);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (selectedCaseId) loadEvidence(selectedCaseId); }, [selectedCaseId, loadEvidence]);

  const filtered = evidence.filter((e) =>
    !filter ||
    e.indicator_value.toLowerCase().includes(filter.toLowerCase()) ||
    e.category.toLowerCase().includes(filter.toLowerCase()) ||
    e.source_name.toLowerCase().includes(filter.toLowerCase())
  );

  const categoryCount: Record<string, number> = {};
  for (const e of evidence) {
    categoryCount[e.category] = (categoryCount[e.category] ?? 0) + 1;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100">OSINT Intelligence</h1>
          <p className="text-xs text-slate-500 mt-0.5">Threat intelligence indicators correlated against known blacklists and IOC databases.</p>
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

      {selectedCaseId && evidence.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(categoryCount).map(([cat, count]) => (
            <button
              key={cat}
              onClick={() => setFilter(filter === cat ? '' : cat)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs transition-colors ${
                filter === cat ? 'border-cyan-700 bg-cyan-950/40 text-cyan-300' : 'border-[#1e293b] bg-[#0d1220] text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>{cat}</span>
              <span className="font-mono">{count}</span>
            </button>
          ))}
          {filter && (
            <button onClick={() => setFilter('')} className="text-xs text-slate-600 hover:text-slate-300 px-2">
              Clear filter ×
            </button>
          )}
        </div>
      )}

      {selectedCaseId && evidence.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
          <input
            type="text"
            placeholder="Search by address, category, or source…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full bg-[#0d1220] border border-[#1e293b] rounded-md pl-9 pr-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-cyan-700 outline-none"
          />
        </div>
      )}

      {!selectedCaseId && <EmptyState icon={<Shield className="w-7 h-7" />} title="No Case Selected" message="Select a case to view correlated OSINT indicators." />}
      {selectedCaseId && loading && <LoadingState message="Loading OSINT indicators…" />}
      {selectedCaseId && !loading && error && <ErrorState title="Evidence Load Failed" message={error} onRetry={() => loadEvidence(selectedCaseId)} />}
      {selectedCaseId && !loading && !error && evidence.length === 0 && (
        <EmptyState icon={<AlertTriangle className="w-7 h-7" />} title="No Evidence Records" message="Ensure this case has been analyzed. OSINT correlation runs during ingestion." />
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs text-slate-500 mb-2">{filtered.length} of {evidence.length} indicators</div>
          {filtered.map((e) => (
            <div
              key={e.evidence_id}
              className="flex items-start gap-4 p-4 bg-[#101624] border border-[#1e293b] rounded-lg hover:border-slate-700 transition-colors"
            >
              <div className="flex-1 min-w-0 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={CATEGORY_VARIANTS[e.category] ?? 'slate'}>{e.category}</Badge>
                  {e.subcategory && <Badge variant="slate" size="sm">{e.subcategory}</Badge>}
                  <span className="text-[10px] text-slate-600 font-mono">{e.indicator_type}</span>
                </div>

                <div className="font-mono text-sm text-cyan-400 break-all">{e.indicator_value}</div>

                {e.description && (
                  <p className="text-xs text-slate-400 leading-relaxed">{e.description}</p>
                )}

                <div className="flex flex-wrap gap-4 text-[11px] text-slate-600">
                  <span>Source: <span className="text-slate-400">{e.source_name}</span></span>
                  <span>Provenance: <span className="text-slate-400">{e.provenance}</span></span>
                  <span>Recorded: <span className="text-slate-400">{formatDateTime(e.created_at)}</span></span>
                </div>
              </div>

              {e.source_url && (
                <a
                  href={e.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 text-slate-500 hover:text-cyan-400 transition-colors p-1"
                  aria-label="Open source"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
