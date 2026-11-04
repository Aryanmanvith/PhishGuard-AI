import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { DemoBadge, RiskBadge } from '../components/Badges';
import { EmptyState, ErrorBanner, PageHeader, Spinner } from '../components/Feedback';
import { useAsync } from '../hooks/useAsync';
import { useToast } from '../hooks/useToast';
import { api } from '../services/api';
import type { RiskCategory } from '../types/api';
import { CATEGORY_HEX, CATEGORY_LABEL, formatDateTime, percent, shortId } from '../utils/format';

const CATEGORIES: RiskCategory[] = ['high', 'suspicious', 'low'];
const TOOLTIP_STYLE = { background: '#101c33', border: '1px solid #22365f', borderRadius: 8, color: '#e2e8f0' };

function StatCard({ label, value, hint, color }: { label: string; value: number | string; hint: string; color?: string }) {
  return (
    <div className="card card-pad">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-bold text-white" style={color ? { color } : undefined}>
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  );
}

export default function DashboardPage() {
  const toast = useToast();
  const stats = useAsync(() => api.stats(), []);
  const recent = useAsync(() => api.listScans({ limit: 6 }), []);
  const [seeding, setSeeding] = useState(false);

  async function seed() {
    setSeeding(true);
    try {
      const res = await api.seedDemo();
      toast.push(res.inserted > 0 ? 'success' : 'info', res.note);
      stats.reload();
      recent.reload();
    } catch (err) {
      toast.push('error', err instanceof Error ? err.message : 'Could not add demo data.');
    } finally {
      setSeeding(false);
    }
  }

  const data = stats.data;
  const pieData = data ? CATEGORIES.map((c) => ({ name: CATEGORY_LABEL[c], key: c, value: data.by_category[c] ?? 0 })).filter((d) => d.value > 0) : [];

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Overview of everything analyzed on this machine. All analysis is static: no link is ever opened."
        actions={
          <>
            <Link to="/url" className="btn-primary">
              Scan a URL
            </Link>
            <Link to="/email" className="btn-secondary">
              Scan an email
            </Link>
          </>
        }
      />

      {stats.loading && !data && <Spinner label="Loading statistics…" />}
      {stats.error && <ErrorBanner message={stats.error} onRetry={stats.reload} />}

      {data && data.total_scans === 0 && (
        <div className="card">
          <EmptyState icon="shield" title="No scans yet">
            Analyze a URL or paste an email to get started, or load a few clearly-labelled demo scans to explore the dashboard.
            <div className="mt-4">
              <button type="button" className="btn-secondary" onClick={seed} disabled={seeding}>
                {seeding ? 'Adding…' : 'Load demo data'}
              </button>
            </div>
          </EmptyState>
        </div>
      )}

      {data && data.total_scans > 0 && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Total scans" value={data.total_scans} hint={`${data.demo_scans} demo · avg score ${data.average_score}`} />
            <StatCard label="High risk" value={data.by_category.high ?? 0} hint={percent(data.by_category.high ?? 0, data.total_scans) + ' of scans'} color={CATEGORY_HEX.high} />
            <StatCard label="Suspicious" value={data.by_category.suspicious ?? 0} hint={percent(data.by_category.suspicious ?? 0, data.total_scans) + ' of scans'} color={CATEGORY_HEX.suspicious} />
            <StatCard label="Lower risk" value={data.by_category.low ?? 0} hint="Not a guarantee of safety" color={CATEGORY_HEX.low} />
          </div>

          <div className="grid gap-5 lg:grid-cols-5">
            <section className="card card-pad lg:col-span-2" aria-label="Risk distribution">
              <h2 className="section-title mb-2">Risk distribution</h2>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2} stroke="none">
                      {pieData.map((d) => (
                        <Cell key={d.key} fill={CATEGORY_HEX[d.key]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="card card-pad lg:col-span-3" aria-label="Scans over time">
              <h2 className="section-title mb-2">Scans, last 14 days</h2>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.last_14_days} margin={{ left: -20, right: 8 }}>
                    <CartesianGrid stroke="#18284a" vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                    <YAxis allowDecimals={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(34,211,238,0.06)' }} />
                    <Legend />
                    <Bar dataKey="total" name="All scans" fill="#33497a" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="high" name="High risk" fill={CATEGORY_HEX.high} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>

          <div className="grid gap-5 lg:grid-cols-5">
            <section className="card card-pad lg:col-span-2">
              <h2 className="section-title mb-3">Most common indicators</h2>
              {data.top_indicators.length === 0 ? (
                <p className="text-sm text-slate-400">No indicators recorded yet.</p>
              ) : (
                <ol className="space-y-2">
                  {data.top_indicators.map((i) => (
                    <li key={i.id} className="flex items-center justify-between gap-3 text-sm">
                      <span className="text-slate-300">{i.title}</span>
                      <span className="chip bg-ink-800 text-slate-200 ring-ink-600">{i.count}</span>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            <section className="card lg:col-span-3">
              <div className="flex items-center justify-between px-4 pt-4 sm:px-5">
                <h2 className="section-title">Recent scans</h2>
                <Link to="/history" className="text-sm font-semibold text-accent hover:text-accent-soft">
                  View all
                </Link>
              </div>
              {recent.loading && !recent.data && <Spinner />}
              {recent.error && (
                <div className="p-4">
                  <ErrorBanner message={recent.error} onRetry={recent.reload} />
                </div>
              )}
              <ul className="divide-y divide-ink-700/60 p-2">
                {recent.data?.items.map((s) => (
                  <li key={s.scan_id}>
                    <Link to={`/history/${s.scan_id}`} className="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-ink-800">
                      <RiskBadge category={s.risk_category} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-mono text-sm text-slate-200">{s.input_summary}</span>
                        <span className="text-xs text-slate-500">
                          {s.input_type} · {formatDateTime(s.created_at)} · {shortId(s.scan_id)}
                        </span>
                      </span>
                      {s.is_demo && <DemoBadge />}
                      <span className="w-8 text-right text-sm font-bold text-slate-100">{s.risk_score}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>
      )}
    </>
  );
}
