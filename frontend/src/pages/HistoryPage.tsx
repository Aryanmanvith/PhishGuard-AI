import { useState } from 'react';
import { Link } from 'react-router-dom';

import { DemoBadge, RiskBadge } from '../components/Badges';
import { EmptyState, ErrorBanner, PageHeader, Spinner } from '../components/Feedback';
import Icon from '../components/Icons';
import { useAsync } from '../hooks/useAsync';
import { useToast } from '../hooks/useToast';
import { api } from '../services/api';
import { formatDateTime, shortId } from '../utils/format';

const PAGE_SIZE = 15;

export default function HistoryPage() {
  const toast = useToast();
  const [offset, setOffset] = useState(0);
  const [category, setCategory] = useState('');
  const [inputType, setInputType] = useState('');
  const [confirmClear, setConfirmClear] = useState(false);

  const list = useAsync(
    () => api.listScans({ limit: PAGE_SIZE, offset, category: category || undefined, inputType: inputType || undefined }),
    [offset, category, inputType],
  );

  async function exportCsv() {
    try {
      await api.downloadHistoryCsv();
      toast.push('success', 'History CSV downloaded.');
    } catch (err) {
      toast.push('error', err instanceof Error ? err.message : 'Export failed.');
    }
  }

  async function clearAll() {
    try {
      const res = await api.clearScans(false);
      toast.push('success', `Deleted ${res.deleted} scan(s).`);
      setConfirmClear(false);
      setOffset(0);
      list.reload();
    } catch (err) {
      toast.push('error', err instanceof Error ? err.message : 'Could not clear history.');
    }
  }

  const data = list.data;
  const total = data?.total ?? 0;

  return (
    <>
      <PageHeader
        title="Scan History"
        subtitle="Every analysis is stored locally in SQLite. Email bodies are never stored, only a short summary."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={exportCsv}>
              <Icon name="download" className="h-4 w-4" /> Export CSV
            </button>
            {!confirmClear ? (
              <button type="button" className="btn-danger" onClick={() => setConfirmClear(true)}>
                <Icon name="trash" className="h-4 w-4" /> Clear history
              </button>
            ) : (
              <span className="flex items-center gap-2">
                <button type="button" className="btn-danger" onClick={clearAll}>
                  Confirm delete all
                </button>
                <button type="button" className="btn-secondary" onClick={() => setConfirmClear(false)}>
                  Cancel
                </button>
              </span>
            )}
          </>
        }
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <div>
          <label htmlFor="filter-category" className="sr-only">
            Risk category
          </label>
          <select
            id="filter-category"
            className="input w-44"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All risk levels</option>
            <option value="high">High risk</option>
            <option value="suspicious">Suspicious</option>
            <option value="low">Low risk</option>
          </select>
        </div>
        <div>
          <label htmlFor="filter-type" className="sr-only">
            Input type
          </label>
          <select
            id="filter-type"
            className="input w-40"
            value={inputType}
            onChange={(e) => {
              setInputType(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">URLs and emails</option>
            <option value="url">URLs only</option>
            <option value="email">Emails only</option>
          </select>
        </div>
      </div>

      {list.error && <ErrorBanner message={list.error} onRetry={list.reload} />}
      {list.loading && !data && <Spinner />}

      {data && data.items.length === 0 && (
        <div className="card">
          <EmptyState icon="history" title="No scans found">
            {category || inputType ? 'No scans match these filters.' : 'Scans you run will appear here.'}
          </EmptyState>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-ink-700 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Input</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3 text-right">Score</th>
                  <th className="px-4 py-3 text-right">ML</th>
                  <th className="px-4 py-3">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-700/60">
                {data.items.map((s) => (
                  <tr key={s.scan_id} className="hover:bg-ink-800/60">
                    <td className="px-4 py-3">
                      <RiskBadge category={s.risk_category} />
                    </td>
                    <td className="max-w-xs px-4 py-3">
                      <Link to={`/history/${s.scan_id}`} className="block truncate font-mono text-slate-100 hover:text-accent">
                        {s.input_summary}
                      </Link>
                      <span className="text-xs text-slate-500">
                        {shortId(s.scan_id)} · {s.indicator_count} indicator(s) {s.is_demo && <DemoBadge />}
                      </span>
                    </td>
                    <td className="px-4 py-3 uppercase text-slate-400">{s.input_type}</td>
                    <td className="px-4 py-3 text-right font-bold text-slate-100">{s.risk_score}</td>
                    <td className="px-4 py-3 text-right text-slate-400">{s.ml_score === null ? '–' : s.ml_score.toFixed(0)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-400">{formatDateTime(s.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-ink-700 px-4 py-3 text-sm text-slate-400">
            <span>
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
            </span>
            <span className="flex gap-2">
              <button type="button" className="btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                Previous
              </button>
              <button type="button" className="btn-secondary" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
                Next
              </button>
            </span>
          </div>
        </div>
      )}
    </>
  );
}
