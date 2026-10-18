import React, { useEffect, useState, useCallback } from 'react';
import { Activity, Cpu, RefreshCw, AlertTriangle, Brain } from 'lucide-react';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import { api, parseApiError } from '@/api/client';
import { MLStatusResponse } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ErrorState, LoadingState } from '@/components/ui/States';
import { StatusDot } from '@/components/ui/RiskBadge';
import { formatDateTime } from '@/lib/utils';

const MetricBar: React.FC<{ label: string; value: number; color?: string }> = ({
  label,
  value,
  color = '#0891b2',
}) => (
  <div className="space-y-1.5">
    <div className="flex justify-between text-xs">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-bold" style={{ color }}>
        {(value * 100).toFixed(2)}%
      </span>
    </div>
    <div className="h-1.5 bg-[#0d1220] rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${value * 100}%`, backgroundColor: color }}
      />
    </div>
  </div>
);

export const ModelHealth: React.FC = () => {
  const [status, setStatus] = useState<MLStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const s = await api.getMLStatus();
      setStatus(s);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const metrics = status?.metrics;

  const radarData = metrics
    ? [
        { metric: 'Accuracy', value: (metrics.accuracy ?? 0) * 100 },
        { metric: 'Precision', value: (metrics.precision ?? 0) * 100 },
        { metric: 'Recall', value: (metrics.recall ?? 0) * 100 },
        { metric: 'F1 Score', value: (metrics.f1_score ?? 0) * 100 },
        { metric: 'ROC-AUC', value: (metrics.auc_roc ?? 0) * 100 },
        { metric: 'Avg Prec.', value: (metrics.average_precision ?? 0) * 100 },
      ]
    : [];

  const barData = metrics?.validation && metrics?.test
    ? [
        { stage: 'Validation', F1: ((metrics.validation as Record<string, number>)?.f1 ?? 0) * 100 },
        { stage: 'Test (0.50)', F1: ((metrics.test as Record<string, number>)?.f1_at_050 ?? metrics.f1_score ?? 0) * 100 },
        { stage: 'Test (0.42)', F1: (metrics.f1_score ?? 0) * 100 },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Model Health & Benchmark</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Live status of GhostTrace's active illicit transaction classifier. Metrics are read-only — do not tune on held-out test set.
          </p>
        </div>
        <Button size="sm" variant="secondary" icon={<RefreshCw className="w-3.5 h-3.5" />} onClick={load} disabled={loading}>
          Refresh
        </Button>
      </div>

      {loading && <LoadingState message="Loading model status…" />}
      {!loading && error && <ErrorState title="ML Status Unavailable" message={error} onRetry={load} />}

      {!loading && !error && status && (
        <div className="space-y-5">
          {/* Identity card */}
          <Card highlight={status.model_loaded ? 'cyan' : 'crimson'}>
            <div className="flex flex-wrap items-center gap-6">
              <div className="w-14 h-14 rounded-xl bg-[#0d1220] border border-cyan-900/60 flex items-center justify-center">
                <Brain className="w-8 h-8 text-cyan-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-lg font-bold text-white">{status.model_name ?? 'GhostTrace Classifier'}</div>
                <div className="flex flex-wrap gap-3 mt-1 text-xs text-slate-500">
                  <span>v{status.version ?? '—'}</span>
                  <span>{status.algorithm ?? '—'}</span>
                  <span>{status.features_count} features</span>
                  <span>{status.network ?? 'bitcoin'} network</span>
                </div>
              </div>
              <div className="flex flex-col gap-2 shrink-0">
                <StatusDot
                  status={status.model_loaded ? 'online' : 'offline'}
                  label={status.model_loaded ? 'Model Loaded' : 'Model Not Loaded'}
                />
                {metrics?.threshold !== undefined && (
                  <span className="text-xs text-slate-400">
                    Inference threshold: <span className="font-mono text-amber-400">{metrics.threshold}</span>
                  </span>
                )}
                {status.training_timestamp && (
                  <span className="text-xs text-slate-600">
                    Trained: {formatDateTime(status.training_timestamp)}
                  </span>
                )}
              </div>
            </div>
          </Card>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {/* Metric bars */}
            {metrics && (
              <Card title="Performance Metrics" subtitle="Held-out chronological test set">
                <div className="space-y-4">
                  <MetricBar label="Accuracy" value={metrics.accuracy ?? 0} color="#0891b2" />
                  <MetricBar label="Illicit Precision" value={metrics.precision ?? 0} color="#7c3aed" />
                  <MetricBar label="Illicit Recall" value={metrics.recall ?? 0} color="#db2777" />
                  <MetricBar label="Illicit F1" value={metrics.f1_score ?? 0} color="#f97316" />
                  <MetricBar label="ROC-AUC" value={metrics.auc_roc ?? 0} color="#059669" />
                  <MetricBar label="Average Precision" value={metrics.average_precision ?? 0} color="#d97706" />
                </div>
              </Card>
            )}

            {/* Radar Chart */}
            {radarData.length > 0 && (
              <Card title="Metric Radar">
                <ResponsiveContainer width="100%" height={250}>
                  <RadarChart data={radarData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                    <PolarGrid stroke="#1e293b" />
                    <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Radar
                      name="Model"
                      dataKey="value"
                      stroke="#0891b2"
                      fill="#0891b2"
                      fillOpacity={0.2}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </Card>
            )}
          </div>

          {/* Val vs Test */}
          {barData.length > 0 && (
            <Card title="Validation vs. Test F1" subtitle="Expect a performance gap due to temporal class-prevalence shift">
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={barData} margin={{ top: 4, right: 4, bottom: 4, left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="stage" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} unit="%" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#101624', border: '1px solid #1e293b', borderRadius: 6, fontSize: 12 }}
                    formatter={(v: any) => [`${(v as number).toFixed(2)}%`, 'F1']}
                  />
                  <Bar dataKey="F1" radius={[3, 3, 0, 0]}>
                    {barData.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? '#7c3aed' : i === 1 ? '#0891b2' : '#059669'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Limitations */}
          <Card title="Evaluation Limitations" highlight="amber">
            <div className="flex items-start gap-2 text-xs text-amber-300">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <p className="leading-relaxed">{status.evaluation_limitations}</p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
