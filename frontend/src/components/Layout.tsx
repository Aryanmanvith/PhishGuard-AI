import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { api } from '../services/api';
import { useAsync } from '../hooks/useAsync';
import Icon, { type IconName } from './Icons';

const NAV: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: '/', label: 'Dashboard', icon: 'grid', end: true },
  { to: '/url', label: 'URL Analyzer', icon: 'link' },
  { to: '/email', label: 'Email Analyzer', icon: 'mail' },
  { to: '/history', label: 'Scan History', icon: 'history' },
  { to: '/model', label: 'ML Model', icon: 'cpu' },
];

function BackendStatus() {
  const { data, error, loading } = useAsync(() => api.health(), []);
  const ok = !!data && data.status === 'ok';
  const text = loading ? 'Connecting…' : ok ? 'Backend online' : 'Backend offline';
  return (
    <span
      className="inline-flex items-center gap-2 text-xs text-slate-400"
      title={error ?? (data ? `Model ${data.model_available ? 'loaded' : 'not trained yet'}` : '')}
    >
      <span
        className={`h-2 w-2 rounded-full ${loading ? 'bg-slate-500' : ok ? 'bg-emerald-400' : 'bg-rose-500'}`}
        aria-hidden="true"
      />
      {text}
    </span>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10 text-accent ring-1 ring-accent/30">
          <Icon name="shield" className="h-5 w-5" />
        </span>
        <div>
          <p className="text-base font-bold leading-tight text-white">PhishGuard AI</p>
          <p className="text-[11px] uppercase tracking-wider text-slate-500">Static threat analysis</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3" aria-label="Main navigation">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                isActive ? 'bg-accent/10 text-accent ring-1 ring-accent/25' : 'text-slate-400 hover:bg-ink-800 hover:text-slate-100'
              }`
            }
          >
            <Icon name={item.icon} className="h-[18px] w-[18px]" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="m-3 rounded-lg border border-ink-700 bg-ink-950/50 p-3 text-xs leading-relaxed text-slate-400">
        <p className="mb-1 flex items-center gap-1.5 font-semibold text-slate-300">
          <Icon name="lock" className="h-3.5 w-3.5" /> Safe by design
        </p>
        URLs are analyzed as text. PhishGuard never opens, fetches or follows them.
      </div>
    </div>
  );
}

export default function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  // Close the mobile drawer whenever the route changes.
  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <div className="min-h-screen lg:pl-64">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-ink-700/70 bg-ink-900/90 lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close menu"
            onClick={() => setOpen(false)}
          />
          <aside className="relative h-full w-64 border-r border-ink-700 bg-ink-900">
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-ink-700/70 bg-ink-950/80 px-4 py-3 backdrop-blur sm:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="rounded-lg p-2 text-slate-300 hover:bg-ink-800 lg:hidden"
            aria-label="Open menu"
            onClick={() => setOpen(true)}
          >
            <Icon name="menu" />
          </button>
          <p className="text-sm font-semibold text-slate-200 lg:hidden">PhishGuard AI</p>
          <p className="hidden text-sm text-slate-400 lg:block">
            Heuristic and ML-assisted analysis. A low score never guarantees safety.
          </p>
        </div>
        <BackendStatus />
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}
