import React, { useState, useEffect } from 'react';
import {
  Brain,
  Sliders,
  Send,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Info,
  Shield,
  Layers,
  FileCode,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { api, parseApiError } from '@/api/client';
import { MLStatusResponse, MLPredictResponse, NetworkType } from '@/types/api';

// Realistic sample feature vectors for Elliptic (165 features)
const PRESETS = [
  {
    name: 'Suspicious Mixing Pattern (High Risk)',
    description: 'High-fanout mixing signature with elevated aggregated incoming/outgoing velocity',
    generator: () => {
      const vec = new Array(165).fill(0);
      vec[0] = 34; // time_step
      // Local features (features 1-93)
      for (let i = 1; i <= 93; i++) {
        vec[i] = Number((Math.sin(i * 1.7) * 2.5 + 1.2).toFixed(4));
      }
      vec[48] = 3.85; // highly elevated feature_48
      vec[56] = 4.12; // highly elevated feature_56
      // Aggregated features (features 94-165)
      for (let i = 94; i < 165; i++) {
        vec[i] = Number((Math.cos(i * 0.9) * 3.1 + 0.8).toFixed(4));
      }
      return vec;
    },
  },
  {
    name: 'Verified Exchange Cold-Storage (Licit)',
    description: 'Standard institutional transfer with standard baseline degree and typical distribution',
    generator: () => {
      const vec = new Array(165).fill(0);
      vec[0] = 20; // time_step
      for (let i = 1; i < 165; i++) {
        vec[i] = Number((Math.sin(i * 0.3) * 0.4 - 0.2).toFixed(4));
      }
      vec[48] = -0.65;
      vec[56] = -0.82;
      return vec;
    },
  },
  {
    name: 'Ransomware Cash-out Cluster (High Anomaly)',
    description: 'Rapid multi-hop dissipation with high aggregated variance in neighbor timesteps',
    generator: () => {
      const vec = new Array(165).fill(0);
      vec[0] = 42; // late time_step
      for (let i = 1; i < 165; i++) {
        vec[i] = Number(((i % 7 === 0 ? 3.2 : 0.1) * (i % 2 === 0 ? 1 : -1)).toFixed(4));
      }
      vec[48] = 4.95;
      vec[56] = 5.21;
      return vec;
    },
  },
  {
    name: 'Zero-Vector Baseline',
    description: 'All 165 features zeroed out (normalized mean baseline)',
    generator: () => new Array(165).fill(0),
  },
];

export const MLInference: React.FC = () => {
  const [mlStatus, setMlStatus] = useState<MLStatusResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [txId, setTxId] = useState('tx_test_88741');
  const [network, setNetwork] = useState<NetworkType>('bitcoin');
  const [threshold, setThreshold] = useState<number>(0.42);
  const [featureValues, setFeatureValues] = useState<number[]>(PRESETS[0].generator());
  const [activePreset, setActivePreset] = useState<number>(0);

  // Prediction result
  const [result, setResult] = useState<MLPredictResponse | null>(null);

  // Fetch ML Status to sync active model info & default threshold
  useEffect(() => {
    async function fetchStatus() {
      try {
        setLoadingStatus(true);
        const st = await api.getMLStatus();
        setMlStatus(st);
        if (st.metrics?.threshold) {
          setThreshold(st.metrics.threshold);
        }
      } catch (err) {
        console.warn('Failed to load ML status', err);
      } finally {
        setLoadingStatus(false);
      }
    }
    fetchStatus();
  }, []);

  const handleSelectPreset = (idx: number) => {
    setActivePreset(idx);
    const vec = PRESETS[idx].generator();
    setFeatureValues(vec);
    setResult(null);
  };

  const handleFeatureChange = (index: number, val: number) => {
    const updated = [...featureValues];
    updated[index] = val;
    setFeatureValues(updated);
  };

  const handleRunInference = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setPredicting(true);
    try {
      const resp = await api.predictTransaction({
        tx_id: txId.trim() || 'tx_adhoc',
        network,
        features: featureValues,
      });

      // Recalculate label locally if custom threshold was adjusted away from server default
      let effectiveLabel = resp.prediction_label;
      let effectiveClass = resp.prediction_class;
      if (threshold !== undefined) {
        effectiveClass = resp.risk_score >= threshold ? 1 : 0;
        effectiveLabel = effectiveClass === 1 ? 'illicit' : 'licit';
      }

      setResult({
        ...resp,
        prediction_label: effectiveLabel,
        prediction_class: effectiveClass,
      });
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setPredicting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-white">Live ML Inference & Triage</h1>
            <Badge variant="cyan">RF v1.1.0</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Real-time heuristic &amp; Random Forest illicit-activity classification against 165 structural/temporal features.
          </p>
        </div>

        {mlStatus && (
          <div className="flex items-center gap-3 bg-[#0d1424] border border-[#1a2336] rounded-lg px-4 py-2">
            <div className="text-right">
              <div className="text-[11px] text-slate-400">Active Model</div>
              <div className="text-xs font-semibold text-slate-200">
                {mlStatus.algorithm || 'Random Forest'} ({mlStatus.version || 'v1.1.0'})
              </div>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div className="text-right">
              <div className="text-[11px] text-slate-400">Calibrated Cutoff</div>
              <div className="text-xs font-bold text-cyan-400">{threshold.toFixed(2)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Dataset & Scope Advisory */}
      <div className="bg-amber-950/20 border border-amber-800/40 rounded-lg p-3.5 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-200/90 leading-relaxed">
          <strong className="text-amber-300">Empirical Boundary Notice:</strong> Model is trained and verified on the Elliptic Bitcoin dataset with a chronological split (held-out test F1: 0.7647 @ 0.42 threshold). Predictions on synthetic or non-Bitcoin networks represent heuristic extrapolations and should not be treated as definitive legal proof.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form: Controls & Presets */}
        <div className="lg:col-span-7 space-y-6">
          <Card title="Inference Parameters & Feature Vector">
            <form onSubmit={handleRunInference} className="space-y-5">
              {/* Target ID & Network */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Transaction / Entity Hash
                  </label>
                  <input
                    type="text"
                    value={txId}
                    onChange={(e) => setTxId(e.target.value)}
                    className="w-full px-3 py-2 bg-[#090d16] border border-[#1e293b] rounded text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
                    placeholder="tx_hex_or_label"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Target Network
                  </label>
                  <select
                    value={network}
                    onChange={(e) => setNetwork(e.target.value as NetworkType)}
                    className="w-full px-3 py-2 bg-[#090d16] border border-[#1e293b] rounded text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="bitcoin">Bitcoin (Calibrated Domain)</option>
                    <option value="ethereum">Ethereum (Experimental)</option>
                    <option value="simulated">Simulated Sandbox</option>
                  </select>
                </div>
              </div>

              {/* Threshold Tuner */}
              <div className="bg-[#090d16] border border-[#1e293b] p-4 rounded-lg space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                    <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                    Decision Threshold:
                  </span>
                  <span className="font-mono font-bold text-cyan-300">{threshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.95"
                  step="0.01"
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg appearance-none"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>0.05 (High Recall)</span>
                  <span className="text-cyan-500 font-semibold">0.42 (Optimal Held-out)</span>
                  <span>0.50 (Default)</span>
                  <span>0.95 (High Precision)</span>
                </div>
              </div>

              {/* Presets Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Feature Vector Presets (165 dimensions)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {PRESETS.map((p, idx) => (
                    <button
                      key={p.name}
                      type="button"
                      onClick={() => handleSelectPreset(idx)}
                      className={`text-left p-2.5 rounded-lg border transition-all text-xs ${
                        activePreset === idx
                          ? 'bg-cyan-950/40 border-cyan-500/80 text-white'
                          : 'bg-[#090d16] border-[#1e293b] text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="font-semibold text-slate-200">{p.name}</div>
                      <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{p.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Key Features Inspection & Quick Edit */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    Key Identified Feature Values
                  </label>
                  <span className="text-[10px] text-slate-500">Showing top discriminatory dimensions</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#090d16] p-3 rounded-lg border border-[#1e293b]">
                  <div>
                    <span className="block text-[10px] text-slate-500">time_step (idx 0)</span>
                    <input
                      type="number"
                      step="1"
                      value={featureValues[0] || 0}
                      onChange={(e) => handleFeatureChange(0, parseFloat(e.target.value) || 0)}
                      className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
                    />
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500">feature_48 (idx 48)</span>
                    <input
                      type="number"
                      step="0.01"
                      value={featureValues[48] || 0}
                      onChange={(e) => handleFeatureChange(48, parseFloat(e.target.value) || 0)}
                      className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
                    />
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500">feature_56 (idx 56)</span>
                    <input
                      type="number"
                      step="0.01"
                      value={featureValues[56] || 0}
                      onChange={(e) => handleFeatureChange(56, parseFloat(e.target.value) || 0)}
                      className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
                    />
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500">feature_1 (idx 1)</span>
                    <input
                      type="number"
                      step="0.01"
                      value={featureValues[1] || 0}
                      onChange={(e) => handleFeatureChange(1, parseFloat(e.target.value) || 0)}
                      className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div className="bg-red-950/40 border border-red-800 text-red-300 text-xs p-3 rounded flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
                  <span>{error}</span>
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                disabled={predicting}
                className="w-full justify-center py-2.5"
              >
                {predicting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                    Executing Random Forest Inference...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    Run Classification &amp; Triage
                  </>
                )}
              </Button>
            </form>
          </Card>
        </div>

        {/* Right Panel: Live Prediction Result & Diagnostics */}
        <div className="lg:col-span-5 space-y-6">
          <Card title="Classification Verdict">
            {result ? (
              <div className="space-y-5">
                {/* Status Hero Card */}
                <div
                  className={`p-5 rounded-xl border text-center transition-all ${
                    result.prediction_label === 'illicit'
                      ? 'bg-red-950/20 border-red-800/80'
                      : 'bg-emerald-950/20 border-emerald-800/80'
                  }`}
                >
                  <div className="flex justify-center mb-2">
                    {result.prediction_label === 'illicit' ? (
                      <div className="w-12 h-12 rounded-full bg-red-900/60 border border-red-500/60 flex items-center justify-center">
                        <AlertTriangle className="w-6 h-6 text-red-400" />
                      </div>
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-emerald-900/60 border border-emerald-500/60 flex items-center justify-center">
                        <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                      </div>
                    )}
                  </div>
                  <div className="text-xs uppercase tracking-widest text-slate-400">Class Verdict</div>
                  <div
                    className={`text-2xl font-black tracking-wide uppercase mt-1 ${
                      result.prediction_label === 'illicit' ? 'text-red-400' : 'text-emerald-400'
                    }`}
                  >
                    {result.prediction_label}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    Risk Probability: <span className="font-mono font-bold text-white">{(result.risk_score * 100).toFixed(1)}%</span>
                  </div>
                </div>

                {/* Score gauge bar */}
                <div className="bg-[#090d16] p-4 rounded-lg border border-[#1e293b] space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400">Model Probability vs. Cutoff</span>
                    <span className="font-mono text-cyan-400">
                      {(result.risk_score * 100).toFixed(1)}% / {(threshold * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="relative w-full h-3 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 rounded-full ${
                        result.prediction_label === 'illicit' ? 'bg-red-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(2, result.risk_score * 100))}%` }}
                    />
                    {/* Vertical marker for threshold */}
                    <div
                      className="absolute top-0 bottom-0 w-1 bg-white shadow-sm"
                      style={{ left: `${threshold * 100}%` }}
                      title={`Active Threshold: ${threshold}`}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>0% (Safe)</span>
                    <span className="text-white font-medium">Cutoff: {(threshold * 100).toFixed(0)}%</span>
                    <span>100% (High Risk)</span>
                  </div>
                </div>

                {/* Metadata & Confidence */}
                <div className="bg-[#090d16] p-3.5 rounded-lg border border-[#1e293b] space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">Target Entity</span>
                    <span className="font-mono text-slate-200">{result.tx_id}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">Model Version</span>
                    <span className="font-semibold text-cyan-400">{result.model_version}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">Network Calibration</span>
                    <span className="text-slate-200 capitalize">{result.network}</span>
                  </div>
                </div>

                {/* Explanation text */}
                <div className="bg-[#090d16] p-3 rounded-lg border border-[#1e293b] text-xs text-slate-300">
                  <div className="font-semibold text-slate-200 mb-1 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-cyan-400" />
                    Model Decision Rationale
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    {result.confidence_explanation}
                  </p>
                </div>

                {/* Statistical Risk Score vs Verified Malicious Label Distinction */}
                <div className="bg-[#0c1220] p-3 rounded-lg border border-cyan-900/40 text-xs">
                  <div className="flex items-center gap-2 mb-1 text-cyan-300 font-semibold">
                    <Shield className="w-3.5 h-3.5 text-cyan-400" />
                    Statistical Score vs. Verified Label
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    Score reflects a model-derived priority score (optimal threshold: 0.42). It is strictly distinguished from verified malicious attribution, which requires verified OSINT correlation.
                  </p>
                </div>

                {result.limitations && (
                  <div className="bg-amber-950/20 border border-amber-800/40 p-3 rounded-lg text-xs text-amber-300/80">
                    <strong className="text-amber-200">Limitations: </strong>
                    {result.limitations}
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 space-y-3">
                <Brain className="w-10 h-10 mx-auto text-slate-600 opacity-60" />
                <div className="text-sm">Awaiting Inference Execution</div>
                <p className="text-xs text-slate-500 max-w-xs mx-auto">
                  Select a test vector preset on the left or customize feature values, then click Run Classification.
                </p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
