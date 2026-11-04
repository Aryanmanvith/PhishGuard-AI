import type { RiskCategory, Severity } from '../types/api';

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(d);
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

export function percent(part: number, total: number): string {
  if (total <= 0) return '0%';
  return `${Math.round((part / total) * 100)}%`;
}

export function formatNumber(n: number, digits = 2): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(digits);
}

/** "Defang" a URL for display so it cannot be clicked or auto-linked by accident. */
export function defang(url: string): string {
  return url.replace(/^http/i, 'hxxp').replace(/\./g, '[.]');
}

export const CATEGORY_LABEL: Record<RiskCategory, string> = {
  low: 'Low risk',
  suspicious: 'Suspicious',
  high: 'High risk',
};

// Full class names (not built dynamically) so Tailwind can see and keep them.
export const CATEGORY_BADGE: Record<RiskCategory, string> = {
  low: 'bg-emerald-400/10 text-emerald-300 ring-emerald-400/30',
  suspicious: 'bg-amber-400/10 text-amber-300 ring-amber-400/30',
  high: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
};

export const CATEGORY_BAR: Record<RiskCategory, string> = {
  low: 'bg-emerald-400',
  suspicious: 'bg-amber-400',
  high: 'bg-rose-500',
};

export const CATEGORY_HEX: Record<RiskCategory, string> = {
  low: '#34d399',
  suspicious: '#fbbf24',
  high: '#f43f5e',
};

export const SEVERITY_BADGE: Record<Severity, string> = {
  info: 'bg-slate-400/10 text-slate-300 ring-slate-400/30',
  low: 'bg-sky-400/10 text-sky-300 ring-sky-400/30',
  medium: 'bg-amber-400/10 text-amber-300 ring-amber-400/30',
  high: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
};
