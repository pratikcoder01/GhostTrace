import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import {
  GitBranch,
  Play,
  Info,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
} from 'lucide-react';
import { api, parseApiError } from '@/api/client';
import { GraphDataResponse, GraphNode, CaseItem } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ErrorState, EmptyState, LoadingState } from '@/components/ui/States';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { useToast } from '@/components/ui/ToastContext';
import { useWebSocket } from '@/context/WebSocketContext';

const RISK_COLORS: Record<string, string> = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#eab308',
  Low: '#10b981',
  Informational: '#64748b',
};

const CLUSTER_PALETTE = ['#0891b2', '#7c3aed', '#db2777', '#d97706', '#059669', '#dc2626', '#4338ca'];

export const TransactionGraph: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { showToast } = useToast();
  const { subscribeToCase, unsubscribeFromCase, registerListener, connectionStatus } = useWebSocket();
  // Use any for the ref to avoid complex ForceGraph generic type conflicts
  const fgRef = useRef<any>(null);

  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>(searchParams.get('caseId') ?? '');
  const [graphData, setGraphData] = useState<GraphDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [colorMode, setColorMode] = useState<'risk' | 'cluster'>('risk');

  useEffect(() => {
    api.listCases().then(setCases).catch(() => {});
  }, []);

  const loadGraph = useCallback(async (caseId: string) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    setGraphData(null);
    setSelectedNode(null);
    try {
      const data = await api.getCaseGraph(caseId);
      setGraphData(data);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadGraph(selectedCaseId);
      subscribeToCase(selectedCaseId);

      const unregisterGraph = registerListener('graph.updated', (msg) => {
        if (msg.case_id === selectedCaseId && msg.data?.graph) {
          setGraphData(msg.data.graph);
          showToast({
            type: 'info',
            title: 'Real-Time Evidence Arrived',
            message: 'Transaction graph updated incrementally via WebSocket.',
          });
        }
      });

      return () => {
        unsubscribeFromCase(selectedCaseId);
        unregisterGraph();
      };
    }
  }, [selectedCaseId, loadGraph, subscribeToCase, unsubscribeFromCase, registerListener, showToast]);

  const handleAnalyze = async () => {
    if (!selectedCaseId) return;
    setAnalyzing(true);
    try {
      await api.analyzeCase(selectedCaseId);
      showToast({ type: 'success', title: 'Analysis Complete', message: 'Graph refreshed with forensic results.' });
      await loadGraph(selectedCaseId);
    } catch (err) {
      showToast({ type: 'error', title: 'Analysis Failed', message: parseApiError(err) });
    } finally {
      setAnalyzing(false);
    }
  };

  const gd = graphData
    ? {
        nodes: graphData.nodes.map((n) => ({
          ...n,
          id: n.id,
          val: Math.max(1, Math.log1p(n.tx_count) * 2),
        })),
        links: graphData.edges.map((e) => ({
          source: typeof e.source === 'string' ? e.source : (e.source as GraphNode).id,
          target: typeof e.target === 'string' ? e.target : (e.target as GraphNode).id,
          tx_id: e.tx_id,
          amount: e.amount,
        })),
      }
    : { nodes: [], links: [] };

  const getNodeColor = (node: GraphNode): string => {
    if (colorMode === 'risk') return RISK_COLORS[node.risk_level] ?? '#64748b';
    return CLUSTER_PALETTE[node.cluster_id % CLUSTER_PALETTE.length] ?? '#64748b';
  };

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] gap-4">
      {/* Controls bar */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-lg font-bold text-slate-100 mr-2">Transaction Graph</h1>

        <select
          value={selectedCaseId}
          onChange={(e) => setSelectedCaseId(e.target.value)}
          className="bg-[#0d1220] border border-[#1e293b] text-sm text-slate-300 rounded-md px-3 py-1.5 focus:border-cyan-700 outline-none min-w-[240px]"
        >
          <option value="">— Select a Case —</option>
          {cases.map((c) => (
            <option key={c.case_id} value={c.case_id}>
              {c.case_name} ({c.status})
            </option>
          ))}
        </select>

        <Button
          size="sm"
          variant="secondary"
          icon={<Play className="w-4 h-4" />}
          onClick={handleAnalyze}
          isLoading={analyzing}
          disabled={!selectedCaseId || analyzing}
        >
          {analyzing ? 'Analyzing…' : 'Run Analysis'}
        </Button>

        <Button
          size="sm"
          variant="ghost"
          icon={<RefreshCw className="w-3.5 h-3.5" />}
          onClick={() => loadGraph(selectedCaseId)}
          disabled={!selectedCaseId || loading}
        >
          Refresh
        </Button>

        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-slate-500">Color by:</span>
          {(['risk', 'cluster'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setColorMode(mode)}
              className={`text-xs px-2 py-1 rounded border transition-colors capitalize ${
                colorMode === mode
                  ? 'border-cyan-700 text-cyan-300 bg-cyan-950/40'
                  : 'border-slate-700 text-slate-500 hover:text-slate-300'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 gap-4 min-h-0">
        {/* Graph canvas */}
        <div className="flex-1 bg-[#08101e] rounded-lg border border-[#1a2336] overflow-hidden relative">
          {!selectedCaseId && (
            <EmptyState
              icon={<GitBranch className="w-7 h-7" />}
              title="No Case Selected"
              message="Select a case above to visualise its transaction graph."
            />
          )}
          {selectedCaseId && loading && <LoadingState message="Building transaction graph…" />}
          {selectedCaseId && !loading && error && (
            <ErrorState title="Graph Load Failed" message={error} onRetry={() => loadGraph(selectedCaseId)} />
          )}
          {selectedCaseId && !loading && !error && graphData && graphData.nodes.length === 0 && (
            <EmptyState
              icon={<GitBranch className="w-7 h-7" />}
              title="No Transactions Traced"
              message='Click "Run Analysis" to execute forensic graph analysis on this case.'
            />
          )}
          {!loading && !error && gd.nodes.length > 0 && (
            <>
              <ForceGraph2D
                ref={fgRef}
                graphData={gd}
                backgroundColor="#08101e"
                nodeLabel={(n: any) => `${(n as GraphNode).id} | ${(n as GraphNode).risk_level} | ${(n as GraphNode).tx_count} tx`}
                nodeColor={(n: any) => getNodeColor(n as GraphNode)}
                nodeVal={(n: any) => (n as any).val ?? 2}
                linkColor={() => 'rgba(100,116,139,0.3)'}
                linkWidth={1}
                linkDirectionalArrowLength={3}
                linkDirectionalArrowRelPos={1}
                onNodeClick={(n: any) => setSelectedNode(n as GraphNode)}
                nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                  const gNode = node as GraphNode;
                  const color = getNodeColor(gNode);
                  const r = Math.max(2, Math.log1p((gNode.tx_count ?? 0)) * 2.5);
                  ctx.beginPath();
                  ctx.arc(gNode.x ?? 0, gNode.y ?? 0, r, 0, 2 * Math.PI);
                  ctx.fillStyle = color;
                  ctx.fill();
                  if ((gNode.is_seed || gNode.risk_level === 'Critical') && globalScale > 0.8) {
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 1.5;
                    ctx.stroke();
                  }
                }}
              />
              {/* Zoom controls */}
              <div className="absolute top-3 right-3 flex flex-col gap-1.5">
                {[
                  { icon: <ZoomIn className="w-3.5 h-3.5" />, fn: () => fgRef.current?.zoom(1.5, 300), label: 'Zoom in' },
                  { icon: <ZoomOut className="w-3.5 h-3.5" />, fn: () => fgRef.current?.zoom(0.75, 300), label: 'Zoom out' },
                  { icon: <Maximize2 className="w-3.5 h-3.5" />, fn: () => fgRef.current?.zoomToFit(400), label: 'Fit' },
                ].map(({ icon, fn, label }) => (
                  <button
                    key={label}
                    onClick={fn}
                    aria-label={label}
                    className="w-7 h-7 bg-[#101624] border border-[#1e293b] rounded flex items-center justify-center text-slate-400 hover:text-white transition-colors"
                  >
                    {icon}
                  </button>
                ))}
              </div>

              {/* Stats overlay */}
              <div className="absolute bottom-3 left-3 flex items-center gap-4 text-xs text-slate-500 bg-[#08101e]/80 backdrop-blur px-3 py-1.5 rounded border border-[#1a2336]">
                <span>{graphData!.node_count} nodes</span>
                <span>{graphData!.edge_count} edges</span>
                <span>{graphData!.clusters_count} clusters</span>
                <span>density {graphData!.density.toFixed(4)}</span>
              </div>
            </>
          )}
        </div>

        {/* Node Inspector */}
        <div className="w-64 shrink-0">
          <Card title="Node Inspector" bodyClassName="space-y-3 text-xs">
            {!selectedNode ? (
              <div className="py-8 text-center text-slate-600">
                <Info className="w-6 h-6 mx-auto mb-2 opacity-40" />
                Click a node to inspect
              </div>
            ) : (
              <>
                <div>
                  <div className="text-slate-500 mb-1">Address</div>
                  <div className="font-mono text-cyan-400 break-all text-[11px]">{selectedNode.id}</div>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Risk</span>
                  <RiskBadge level={selectedNode.risk_level} score={selectedNode.priority_score} />
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Cluster</span>
                  <span className="text-slate-300">{selectedNode.cluster_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Transactions</span>
                  <span className="text-slate-300">{selectedNode.tx_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">In-degree</span>
                  <span className="text-slate-300">{selectedNode.in_degree}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Out-degree</span>
                  <span className="text-slate-300">{selectedNode.out_degree}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Inflow</span>
                  <span className="text-emerald-400">{selectedNode.total_inflow.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Outflow</span>
                  <span className="text-red-400">{selectedNode.total_outflow.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">OSINT Hits</span>
                  <span className={selectedNode.osint_hits > 0 ? 'text-amber-400' : 'text-slate-500'}>
                    {selectedNode.osint_hits}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Seed Node</span>
                  <span className={selectedNode.is_seed ? 'text-cyan-400' : 'text-slate-600'}>
                    {selectedNode.is_seed ? 'Yes' : 'No'}
                  </span>
                </div>
              </>
            )}
          </Card>

          {/* Legend */}
          {graphData && (
            <Card title="Risk Legend" className="mt-3" bodyClassName="space-y-1.5">
              {Object.entries(RISK_COLORS).map(([lvl, color]) => (
                <div key={lvl} className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
                  <span className="text-slate-400">{lvl}</span>
                </div>
              ))}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
