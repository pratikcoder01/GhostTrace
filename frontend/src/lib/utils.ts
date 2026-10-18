export function truncateAddress(addr: string, start = 6, end = 4): string {
  if (!addr) return '';
  if (addr.length <= start + end + 3) return addr;
  return `${addr.slice(0, start)}...${addr.slice(-end)}`;
}

export function formatAmount(val?: number, asset = 'ETH'): string {
  if (val === undefined || val === null) return '0.00 ' + asset;
  return `${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })} ${asset}`;
}

export function formatDateTime(isoStr?: string): string {
  if (!isoStr) return 'N/A';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return isoStr;
  }
}

export function getRiskColor(level?: string): {
  bg: string;
  text: string;
  border: string;
} {
  switch (level?.toLowerCase()) {
    case 'critical':
      return { bg: 'bg-red-950/60', text: 'text-red-400', border: 'border-red-800/80' };
    case 'high':
      return { bg: 'bg-amber-950/60', text: 'text-amber-400', border: 'border-amber-800/80' };
    case 'medium':
      return { bg: 'bg-yellow-950/60', text: 'text-yellow-400', border: 'border-yellow-800/80' };
    case 'low':
      return { bg: 'bg-emerald-950/60', text: 'text-emerald-400', border: 'border-emerald-800/80' };
    default:
      return { bg: 'bg-slate-900', text: 'text-slate-400', border: 'border-slate-800' };
  }
}

export function downloadJsonFile(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
