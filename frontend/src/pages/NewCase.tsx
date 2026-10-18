import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { FolderPlus, AlertCircle, Info, CheckCircle2 } from 'lucide-react';
import { api, parseApiError } from '@/api/client';
import { DataSourceItem } from '@/types/api';
import { caseCreateSchema, CaseCreateFormData } from '@/schemas/caseSchema';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useToast } from '@/components/ui/ToastContext';

const NETWORK_OPTIONS = [
  { value: 'simulated', label: 'Simulated (Synthetic Scenarios)', description: 'Use deterministic ghost-attack scenarios' },
  { value: 'bitcoin', label: 'Bitcoin (Elliptic Dataset)', description: 'Real BTC transaction data from Elliptic AML dataset' },
  { value: 'ethereum', label: 'Ethereum (Etherscan Adapter)', description: 'Bounded live ETH data via Etherscan API (offline if key missing)' },
];

export const NewCase: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [sources, setSources] = useState<DataSourceItem[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<CaseCreateFormData>({
    resolver: zodResolver(caseCreateSchema),
    defaultValues: {
      network: 'simulated',
      data_source: 'synthetic_ghost_attack',
    },
  });

  const selectedNetwork = watch('network');
  const selectedSource = watch('data_source');

  useEffect(() => {
    api.getDataSources().then((res) => setSources(res.data_sources)).finally(() => setSourcesLoading(false));
  }, []);

  const selectedSourceInfo = sources.find((s) => s.id === selectedSource);

  const onSubmit = async (data: CaseCreateFormData) => {
    setCreating(true);
    try {
      const seedAddresses = data.seed_address_raw
        .split('\n')
        .map((a) => a.trim())
        .filter(Boolean);

      const created = await api.createCase({
        case_name: data.case_name,
        description: data.description,
        network: data.network,
        seed_addresses: seedAddresses,
        data_source: data.data_source,
      });

      showToast({ type: 'success', title: 'Case Created', message: `${created.case_name} (${created.case_id.slice(0, 8)}…) — navigating to graph.` });
      navigate(`/graph?caseId=${created.case_id}`);
    } catch (err) {
      showToast({ type: 'error', title: 'Case Creation Failed', message: parseApiError(err) });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100 tracking-tight">New Investigation Case</h1>
        <p className="text-xs text-slate-500 mt-0.5">Configure seed wallets, data sources, and tracing parameters.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Case Identity */}
        <Card title="Case Identity">
          <div className="space-y-4">
            <div>
              <label htmlFor="case_name" className="block text-xs font-medium text-slate-300 mb-1.5">
                Case Name <span className="text-red-400">*</span>
              </label>
              <input
                id="case_name"
                type="text"
                {...register('case_name')}
                placeholder="Operation Phantom Drain"
                className="w-full bg-[#0d1220] border border-[#1e293b] rounded-md px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-cyan-700 focus:ring-1 focus:ring-cyan-700 outline-none transition-colors"
              />
              {errors.case_name && (
                <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" /> {errors.case_name.message}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="description" className="block text-xs font-medium text-slate-300 mb-1.5">
                Description
              </label>
              <textarea
                id="description"
                {...register('description')}
                rows={3}
                placeholder="Brief description of investigative context and goals…"
                className="w-full bg-[#0d1220] border border-[#1e293b] rounded-md px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-cyan-700 focus:ring-1 focus:ring-cyan-700 outline-none resize-none transition-colors"
              />
            </div>
          </div>
        </Card>

        {/* Network Selection */}
        <Card title="Blockchain Network">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {NETWORK_OPTIONS.map((net) => (
              <label
                key={net.value}
                className={`relative flex flex-col gap-1 p-3 rounded-lg border cursor-pointer transition-all duration-150
                  ${selectedNetwork === net.value
                    ? 'border-cyan-700 bg-cyan-950/30'
                    : 'border-[#1e293b] bg-[#0d1220] hover:border-slate-700'
                  }`}
              >
                <input type="radio" {...register('network')} value={net.value} className="sr-only" />
                <span className="text-sm font-medium text-slate-200">{net.label.split('(')[0]}</span>
                <span className="text-[11px] text-slate-500">{net.description}</span>
              </label>
            ))}
          </div>
          {errors.network && (
            <p className="mt-2 text-xs text-red-400">{errors.network.message}</p>
          )}
        </Card>

        {/* Seed Addresses */}
        <Card title="Seed Wallet Addresses" subtitle="One address per line — the investigation starting points">
          <label htmlFor="seed_address_raw" className="sr-only">Seed addresses</label>
          <textarea
            id="seed_address_raw"
            {...register('seed_address_raw')}
            rows={5}
            placeholder={`0xSIM_VICTIM_VAULT_01\n0xSIM_VICTIM_VAULT_02\n…`}
            className="w-full font-mono text-xs bg-[#0d1220] border border-[#1e293b] rounded-md px-3 py-2 text-slate-200 placeholder-slate-600 focus:border-cyan-700 focus:ring-1 focus:ring-cyan-700 outline-none resize-y transition-colors"
            spellCheck={false}
          />
          {errors.seed_address_raw && (
            <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> {errors.seed_address_raw.message}
            </p>
          )}
          <p className="mt-2 text-[11px] text-slate-600 flex items-center gap-1">
            <Info className="w-3 h-3" />
            Addresses are used as graph traversal seeds only. Do not attribute identity based on address alone.
          </p>
        </Card>

        {/* Data Source */}
        <Card title="Intelligence Data Source">
          {sourcesLoading ? (
            <div className="text-xs text-slate-500">Loading data sources…</div>
          ) : (
            <div className="space-y-2">
              {sources.map((src) => (
                <label
                  key={src.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-150
                    ${selectedSource === src.id
                      ? 'border-cyan-700 bg-cyan-950/20'
                      : 'border-[#1e293b] bg-[#0d1220] hover:border-slate-700'
                    }
                    ${!src.available ? 'opacity-50' : ''}
                  `}
                >
                  <input
                    type="radio"
                    {...register('data_source')}
                    value={src.id}
                    disabled={!src.available}
                    className="mt-0.5 accent-cyan-500"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-slate-200">{src.name}</span>
                      <Badge variant={src.available ? 'emerald' : 'crimson'} size="sm">
                        {src.available ? 'Available' : 'Unavailable'}
                      </Badge>
                      <span className="text-[10px] text-slate-600 font-mono">{src.network}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{src.description}</p>
                  </div>
                </label>
              ))}
            </div>
          )}

          {selectedSourceInfo && !selectedSourceInfo.available && (
            <div className="mt-3 flex items-start gap-2 p-3 rounded bg-red-950/40 border border-red-900/60">
              <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
              <div className="text-xs text-red-300">
                <strong>Source Unavailable:</strong> The selected data source is not present on disk. Case creation will fail. Please select an available source or provision the dataset first.
              </div>
            </div>
          )}
        </Card>

        {/* Submit */}
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-slate-600 max-w-sm">
            Creating a case will ingest transaction data, correlate OSINT indicators, and commit genesis blocks to the TraceChain audit ledger.
          </p>
          <Button
            type="submit"
            isLoading={creating}
            icon={<FolderPlus className="w-4 h-4" />}
            size="lg"
          >
            {creating ? 'Creating Case…' : 'Create Investigation'}
          </Button>
        </div>
      </form>
    </div>
  );
};
