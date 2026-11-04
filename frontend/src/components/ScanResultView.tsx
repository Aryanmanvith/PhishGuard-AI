import { api } from '../services/api';
import { useToast } from '../hooks/useToast';
import type { EmailLink, ScanResult } from '../types/api';
import { CATEGORY_BADGE, CATEGORY_LABEL, formatDateTime, formatNumber, shortId } from '../utils/format';
import { DemoBadge, RiskBadge, SeverityBadge } from './Badges';
import Icon from './Icons';
import ScoreGauge from './ScoreGauge';

function isEmailLinks(value: unknown): value is EmailLink[] {
  return Array.isArray(value);
}

/** Full explanation of one scan: score, indicators, ML comparison, links, limitations. */
export default function ScanResultView({ scan }: { scan: ScanResult }) {
  const toast = useToast();
  const links = isEmailLinks(scan.details.links) ? scan.details.links : [];

  async function onDownload() {
    try {
      await api.downloadScanReport(scan.scan_id);
      toast.push('success', 'Report downloaded.');
    } catch (err) {
      toast.push('error', err instanceof Error ? err.message : 'Download failed.');
    }
  }

  return (
    <div className="space-y-5">
      <section className="card card-pad">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <ScoreGauge score={scan.risk_score} category={scan.risk_category} />
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <RiskBadge category={scan.risk_category} />
              <span className="chip bg-ink-800 text-slate-300 ring-ink-600 uppercase">{scan.input_type}</span>
              {scan.is_demo && <DemoBadge />}
            </div>
            <p className="break-all font-mono text-sm text-slate-100" data-testid="input-summary">
              {scan.input_summary}
            </p>
            <p className="mt-2 text-xs text-slate-400">
              Analyzed {formatDateTime(scan.analyzed_at)} · Scan {shortId(scan.scan_id)} · Confidence:{' '}
              <span className="font-semibold text-slate-300">{scan.confidence.level}</span>
            </p>
            <p className="mt-1 text-xs text-slate-400">{scan.confidence.note}</p>
            <button type="button" className="btn-secondary mt-3" onClick={onDownload}>
              <Icon name="download" className="h-4 w-4" /> Download JSON report
            </button>
          </div>
        </div>
        <p className="mt-4 rounded-lg bg-amber-400/5 p-3 text-xs text-amber-200/90 ring-1 ring-inset ring-amber-400/20">
          This 0–100 value is a transparent heuristic score built from the indicators below. It is not a probability, and a
          low score does not guarantee a link or message is safe.
        </p>
      </section>

      <section className="card card-pad">
        <h2 className="section-title mb-3">Indicators ({scan.indicators.length})</h2>
        {scan.indicators.length === 0 ? (
          <p className="text-sm text-slate-400">
            No heuristic indicators fired. That is not proof of safety: attackers can use clean-looking links.
          </p>
        ) : (
          <ul className="space-y-3">
            {scan.indicators.map((ind) => (
              <li key={ind.id} className="rounded-lg border border-ink-700 bg-ink-950/40 p-3.5">
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={ind.severity} />
                  <h3 className="text-sm font-semibold text-slate-100">{ind.title}</h3>
                  <span className="ml-auto text-xs font-semibold text-slate-400">+{ind.points} pts</span>
                </div>
                {ind.evidence && (
                  <p className="mt-2 break-all rounded bg-ink-900 px-2 py-1 font-mono text-xs text-accent-soft">{ind.evidence}</p>
                )}
                <p className="mt-2 text-sm text-slate-300">{ind.explanation}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {scan.ml && (
        <section className="card card-pad">
          <h2 className="section-title mb-3">Machine-learning check</h2>
          {scan.ml.available ? (
            <>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <span className="text-2xl font-bold text-white">{formatNumber(scan.ml.score ?? 0, 1)}</span>
                <span className="chip bg-ink-800 text-slate-200 ring-ink-600">{scan.ml.label}</span>
                <span className="text-xs text-slate-400">{scan.ml.model_name}</span>
                {scan.ml.trained_on_demo_data && (
                  <span className="chip bg-violet-400/10 text-violet-300 ring-violet-400/30">Trained on demo sample data</span>
                )}
              </div>
              {scan.comparison && (
                <p
                  className={`mt-3 rounded-lg p-3 text-sm ring-1 ring-inset ${
                    scan.comparison.status === 'agree'
                      ? 'bg-emerald-400/5 text-emerald-200 ring-emerald-400/20'
                      : 'bg-amber-400/5 text-amber-200 ring-amber-400/20'
                  }`}
                >
                  <strong className="capitalize">{scan.comparison.status}:</strong> {scan.comparison.summary}
                </p>
              )}
              {scan.ml.top_features.length > 0 && (
                <div className="mt-4">
                  <h3 className="mb-2 text-sm font-semibold text-slate-200">What pushed the model's output</h3>
                  <ul className="space-y-1.5">
                    {scan.ml.top_features.map((f) => (
                      <li key={f.feature} className="flex items-center justify-between gap-3 text-sm">
                        <span className="text-slate-300">
                          {f.label} <span className="text-slate-500">= {formatNumber(f.value)}</span>
                        </span>
                        <span className={f.direction === 'raises' ? 'font-semibold text-rose-300' : 'font-semibold text-emerald-300'}>
                          {f.direction} ({f.contribution > 0 ? '+' : ''}
                          {f.contribution.toFixed(2)})
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <p className="mt-3 text-xs text-slate-500">{scan.ml.note}</p>
            </>
          ) : (
            <p className="text-sm text-slate-400">{scan.ml.note}</p>
          )}
        </section>
      )}

      {links.length > 0 && (
        <section className="card card-pad">
          <h2 className="section-title mb-3">Links found in the message ({links.length})</h2>
          <ul className="space-y-2">
            {links.map((l) => (
              <li key={l.url} className="flex flex-wrap items-center gap-2 rounded-lg border border-ink-700 bg-ink-950/40 p-3">
                <span className={`chip ${CATEGORY_BADGE[l.risk_category]}`}>
                  {l.risk_score} · {CATEGORY_LABEL[l.risk_category]}
                </span>
                {/* Plain text on purpose: never render untrusted URLs as clickable links. */}
                <span className="min-w-0 flex-1 break-all font-mono text-xs text-slate-300">{l.url}</span>
                {l.top_indicators.length > 0 && <span className="w-full text-xs text-slate-400">{l.top_indicators.join(' · ')}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="card card-pad">
        <h2 className="section-title mb-3">Limitations</h2>
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-400">
          {scan.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
