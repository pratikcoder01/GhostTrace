import React, { useState, useEffect, useCallback } from 'react';
import { Wallet, Search, ArrowUpRight, ArrowDownLeft, Shield, RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { api, parseApiError } from '@/api/client';
import { WalletItem, CaseItem } from '@/types/api';

const RISK_BADGE: Record<string, 'crimson' | 'amber' | 'emerald' | 'slate'> = {
  Critical: 'crimson',
  High: 'amber',
  Medium: 'amber',
  Low: 'emerald',
};

export const WalletExplorer: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [wallets, setWallets] = useState<WalletItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

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

  const loadWallets = useCallback(async (caseId: string) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCaseMatrices(caseId);
      setWallets(res.wallets || []);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadWallets(selectedCaseId);
    }
  }, [selectedCaseId, loadWallets]);

  const filtered = wallets.filter((w) => {
    const matchesQuery =
      !query ||
      w.address.toLowerCase().includes(query.toLowerCase()) ||
      w.label.toLowerCase().includes(query.toLowerCase()) ||
      w.category.toLowerCase().includes(query.toLowerCase());
    const matchesCat = categoryFilter === 'all' || w.category === categoryFilter;
    return matchesQuery && matchesCat;
  });

  return (
    <div className="space-y-6">
      {/* Header and Case Selector */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Wallet className="w-3.5 h-3.5" />
            <span>ON-CHAIN WALLET INTELLIGENCE</span>
          </div>
          <h1 className="text-xl font-bold text-slate-100">Wallet Explorer</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Inspect individual wallet nodes, balance flows, topological hop depth, and risk assignments derived from graph analysis.
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
            onClick={() => loadWallets(selectedCaseId)}
            disabled={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search by address, classification, or label…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-[#0c1c2f] border border-[#263649] rounded-md pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          {['all', 'SEED', 'RELAY', 'CANDIDATE_EXIT'].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-colors ${
                categoryFilter === cat
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                  : 'bg-[#102033] text-slate-400 border border-[#263649] hover:text-slate-200'
              }`}
            >
              {cat === 'all' ? 'All Roles' : cat}
            </button>
          ))}
        </div>
      </div>

      {loading && <LoadingState message="Loading wallet entities from graph…" />}
      {error && <ErrorState title="Failed to Load Wallets" message={error} onRetry={() => loadWallets(selectedCaseId)} />}

      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((wallet) => (
            <Card
              key={wallet.id}
              title={
                <div className="flex items-center gap-2">
                  <Wallet className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span className="font-mono text-xs text-slate-200 truncate">{wallet.address}</span>
                </div>
              }
              action={
                <Badge variant={RISK_BADGE[wallet.risk_level || 'Low'] || 'slate'} size="sm">
                  {wallet.risk_level || 'Low'}
                </Badge>
              }
              bodyClassName="space-y-3 text-xs"
            >
              <div>
                <div className="text-slate-300 font-semibold text-xs mb-1">{wallet.label}</div>
                <div className="text-[11px] text-slate-500">{wallet.notes}</div>
              </div>

              <div className="grid grid-cols-2 gap-3 py-2 border-y border-[#1b2b3e]">
                <div>
                  <div className="flex items-center gap-1 text-[10px] text-slate-400 mb-0.5">
                    <ArrowDownLeft className="w-3 h-3 text-emerald-400" />
                    <span>Inflow</span>
                  </div>
                  <div className="font-mono text-emerald-300 font-bold">
                    {wallet.inflow ? `${wallet.inflow.toLocaleString()} ETH` : '0 ETH'}
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-1 text-[10px] text-slate-400 mb-0.5">
                    <ArrowUpRight className="w-3 h-3 text-cyan-400" />
                    <span>Outflow</span>
                  </div>
                  <div className="font-mono text-cyan-300 font-bold">
                    {wallet.outflow ? `${wallet.outflow.toLocaleString()} ETH` : '0 ETH'}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>
                  Role: <strong className="text-slate-200 font-mono">{wallet.category}</strong>
                </span>
                <span>
                  Tx Count: <strong className="text-slate-200 font-mono">{wallet.tx_count}</strong>
                </span>
              </div>
            </Card>
          ))}

          {filtered.length === 0 && (
            <div className="col-span-full text-center text-slate-500 text-sm py-12">
              No wallet nodes match your search query.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
