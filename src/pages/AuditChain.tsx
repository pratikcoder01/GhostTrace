import React, { useEffect, useState, useCallback } from 'react';
import { Shield, CheckCircle2, AlertTriangle, Hash, ExternalLink, RefreshCw, Copy, Check, Bug, Undo2 } from 'lucide-react';
import { api, parseApiError } from '@/api/client';
import { TraceChainBlock, TraceChainVerifyResponse, DemoTamperResponse, DemoResetResponse } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ErrorState, LoadingState } from '@/components/ui/States';
import { formatDateTime, truncateAddress } from '@/lib/utils';
import { useWebSocket } from '@/context/WebSocketContext';

const EVENT_COLORS: Record<string, 'cyan' | 'emerald' | 'amber' | 'purple' | 'slate'> = {
  GENESIS: 'cyan',
  CASE_CREATED: 'emerald',
  CASE_ANALYZED: 'purple',
  INGESTION: 'amber',
};

export const AuditChain: React.FC = () => {
  const [blocks, setBlocks] = useState<TraceChainBlock[]>([]);
  const [verify, setVerify] = useState<TraceChainVerifyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  // Demo Tamper state
  const [demoStatus, setDemoStatus] = useState<{ isTampered: boolean; message: string; details: string } | null>(null);
  const [demoActionLoading, setDemoActionLoading] = useState(false);

  const { registerListener } = useWebSocket();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [b, v] = await Promise.all([api.getBlocks(), api.verifyChain()]);
      setBlocks(b.reverse());
      setVerify(v);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Live WebSocket update on new mined blocks
  useEffect(() => {
    const cleanup = registerListener('audit.updated', () => {
      load();
    });
    return cleanup;
  }, [registerListener, load]);

  const handleDemoTamper = async () => {
    setDemoActionLoading(true);
    try {
      const res = await api.demoTamper();
      setDemoStatus({
        isTampered: true,
        message: res.message,
        details: res.details,
      });
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setDemoActionLoading(false);
    }
  };

  const handleDemoReset = async () => {
    setDemoActionLoading(true);
    try {
      const res = await api.demoReset();
      setDemoStatus({
        isTampered: false,
        message: res.message,
        details: res.details,
      });
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setDemoActionLoading(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const v = await api.verifyChain();
      setVerify(v);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setVerifying(false);
    }
  };

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash).then(() => {
      setCopiedHash(hash);
      setTimeout(() => setCopiedHash(null), 2000);
    });
  };

  const toggleBlock = (index: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(index) ? next.delete(index) : next.add(index);
      return next;
    });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100">TraceChain Audit Ledger</h1>
          <p className="text-xs text-slate-500 mt-0.5">Immutable SHA-256 hash-linked forensic audit trail. Proof-of-work anchored.</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={load} disabled={loading}>
            Refresh
          </Button>
          <Button size="sm" variant="primary" icon={<Shield className="w-3.5 h-3.5" />} onClick={handleVerify} isLoading={verifying}>
            Verify Integrity
          </Button>
        </div>
      </div>

      {loading && <LoadingState message="Loading TraceChain blocks…" />}
      {!loading && error && <ErrorState title="Chain Load Failed" message={error} onRetry={load} />}

      {!loading && !error && (
        <>
          {/* Verification banner */}
          {verify && (
            <div className={`flex items-start gap-3 p-4 rounded-lg border ${
              verify.is_valid
                ? 'bg-emerald-950/30 border-emerald-800/50'
                : 'bg-red-950/30 border-red-800/50'
            }`}>
              {verify.is_valid ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <div className={`font-semibold text-sm ${verify.is_valid ? 'text-emerald-300' : 'text-red-300'}`}>
                  {verify.is_valid ? 'Chain Integrity Verified' : 'Chain Integrity Compromised'}
                </div>
                <div className="text-xs text-slate-400 mt-0.5">{verify.details}</div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs shrink-0">
                <div className="text-center">
                  <div className="text-slate-400 font-mono text-base">{verify.total_blocks}</div>
                  <div className="text-slate-600">Blocks</div>
                </div>
                <div className="text-center">
                  <div className={`font-mono text-base ${verify.genesis_valid ? 'text-emerald-400' : 'text-red-400'}`}>
                    {verify.genesis_valid ? '✓' : '✗'}
                  </div>
                  <div className="text-slate-600">Genesis</div>
                </div>
              </div>
            </div>
          )}

          {/* Interactive Cryptographic Tamper Demo */}
          <div className="p-4 bg-[#102033] border border-[#263649] rounded-lg space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <Bug className="w-4 h-4 text-amber-400" />
                <span className="font-semibold text-sm text-slate-100">
                  Cryptographic Tamper-Detection Demonstration
                </span>
                <Badge variant="slate" size="sm">ISOLATED DEMO LEDGER</Badge>
              </div>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="danger"
                  icon={<Bug className="w-3.5 h-3.5" />}
                  onClick={handleDemoTamper}
                  isLoading={demoActionLoading}
                >
                  Tamper Block #1 (Demo)
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  icon={<Undo2 className="w-3.5 h-3.5" />}
                  onClick={handleDemoReset}
                  isLoading={demoActionLoading}
                >
                  Reset Demo Chain
                </Button>
              </div>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Demonstrates zero-trust mathematical integrity: modifies the payload of block #1 without re-mining proof-of-work.
              TraceChain's sequential SHA-256 hash continuity detects the anomaly instantly upon verification.
            </p>

            {demoStatus && (
              <div className={`p-3 rounded border text-xs font-mono flex items-start gap-2.5 ${
                demoStatus.isTampered
                  ? 'bg-red-950/40 border-red-800/60 text-red-300'
                  : 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
              }`}>
                {demoStatus.isTampered ? (
                  <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                )}
                <div className="space-y-0.5">
                  <div className="font-bold">{demoStatus.message}</div>
                  <div className="text-[11px] opacity-80">{demoStatus.details}</div>
                </div>
              </div>
            )}
          </div>

          {/* Blocks */}
          <div className="space-y-2">
            {blocks.map((block) => {
              const isOpen = expanded.has(block.index);
              return (
                <div
                  key={block.index}
                  className={`bg-[#101624] border rounded-lg overflow-hidden transition-colors
                    ${block.index === 0 ? 'border-cyan-900/60' : 'border-[#1e293b]'}
                  `}
                >
                  <button
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[#141d2e] transition-colors"
                    onClick={() => toggleBlock(block.index)}
                  >
                    <span className="text-xs font-mono text-slate-600 w-8 text-right shrink-0">#{block.index}</span>
                    <Badge variant={EVENT_COLORS[block.event_type] ?? 'slate'}>
                      {block.event_type}
                    </Badge>
                    {block.case_id && (
                      <span className="text-xs font-mono text-slate-500 truncate">{block.case_id.slice(0, 12)}…</span>
                    )}
                    <div className="flex-1" />
                    <div className="flex items-center gap-3 shrink-0">
                      <div className="flex items-center gap-1.5 text-xs font-mono text-slate-500">
                        <Hash className="w-3 h-3" />
                        {block.hash.slice(0, 12)}…
                      </div>
                      <span className="text-xs text-slate-600">{formatDateTime(block.timestamp)}</span>
                    </div>
                  </button>

                  {isOpen && (
                    <div className="px-4 pb-4 border-t border-[#1a2336] pt-3 space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div>
                          <div className="text-slate-500 mb-1">Hash</div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-cyan-400 break-all text-[11px]">{block.hash}</span>
                            <button
                              onClick={() => copyHash(block.hash)}
                              className="shrink-0 text-slate-500 hover:text-slate-200 transition-colors"
                              aria-label="Copy hash"
                            >
                              {copiedHash === block.hash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            </button>
                          </div>
                        </div>
                        <div>
                          <div className="text-slate-500 mb-1">Previous Hash</div>
                          <div className="font-mono text-slate-400 break-all text-[11px]">{block.previous_hash}</div>
                        </div>
                        <div>
                          <div className="text-slate-500 mb-1">Nonce (PoW)</div>
                          <div className="font-mono text-amber-400">{block.nonce}</div>
                        </div>
                        <div>
                          <div className="text-slate-500 mb-1">Difficulty</div>
                          <div className="font-mono text-slate-300">{block.difficulty}</div>
                        </div>
                      </div>

                      <div>
                        <div className="text-slate-500 text-xs mb-1">Payload</div>
                        <pre className="text-[11px] font-mono text-slate-400 bg-[#0d1220] px-3 py-2 rounded border border-[#1a2336] overflow-auto max-h-48">
                          {JSON.stringify(block.payload, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {blocks.length === 0 && (
            <div className="text-center text-slate-500 text-sm py-12">
              No blocks mined yet. Create and analyze a case to generate audit blocks.
            </div>
          )}
        </>
      )}
    </div>
  );
};
