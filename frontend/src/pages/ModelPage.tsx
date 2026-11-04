import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { EmptyState, ErrorBanner, PageHeader, Spinner } from '../components/Feedback';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import type { ModelMetrics } from '../types/api';

const TOOLTIP_STYLE = { background: '#101c33', border: '1px solid #22365f', borderRadius: 8, color: '#e2e8f0' };
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

function MetricsBlock({ title, m }: { title: string; m: ModelMetrics }) {
  const [[tn, fp], [fn, tp]] = m.confusion_matrix;
  return (
    <section className="card card-pad">
      <h3 className="mb-3 text-base font-semibold text-white">{title}</h3>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          ['Precision', pct(m.precision)],
          ['Recall', pct(m.recall)],
          ['F1', pct(m.f1)],
          ['Accuracy', pct(m.accuracy)],
          ['ROC-AUC', m.roc_auc === null ? 'n/a' : m.roc_auc.toFixed(3)],
        ].map(([k, v]) => (
          <div key={k} className="rounded-lg bg-ink-950/50 p-3">
            <dt className="text-xs uppercase tracking-wide text-slate-400">{k}</dt>
            <dd className="mt-1 text-xl font-bold text-slate-100">{v}</dd>
          </div>
        ))}
      </dl>
      <h4 className="section-title mb-2 mt-4">Confusion matrix ({m.n_test} test rows)</h4>
      <table className="w-full max-w-sm border-separate border-spacing-1 text-center text-sm" aria-label="Confusion matrix">
        <thead>
          <tr className="text-xs text-slate-400">
            <th />
            <th>Predicted benign</th>
            <th>Predicted phishing</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th className="text-left text-xs text-slate-400">Actually benign</th>
            <td className="rounded bg-emerald-400/10 py-2 font-bold text-emerald-300">{tn}</td>
            <td className="rounded bg-rose-500/10 py-2 font-bold text-rose-300">{fp}</td>
          </tr>
          <tr>
            <th className="text-left text-xs text-slate-400">Actually phishing</th>
            <td className="rounded bg-rose-500/10 py-2 font-bold text-rose-300">{fn}</td>
            <td className="rounded bg-emerald-400/10 py-2 font-bold text-emerald-300">{tp}</td>
          </tr>
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-500">Decision threshold {m.threshold}. Computed on the held-out test set only.</p>
    </section>
  );
}

export default function ModelPage() {
  const model = useAsync(() => api.model(), []);
  const info = model.data;

  return (
    <>
      <PageHeader
        title="ML Model"
        subtitle="Metrics are read from the training run saved on disk. Nothing here is hard-coded."
      />
      {model.loading && <Spinner label="Loading model details…" />}
      {model.error && <ErrorBanner message={model.error} onRetry={model.reload} />}

      {info && !info.available && (
        <div className="card">
          <EmptyState icon="cpu" title="No trained model found">
            {info.reason}
            <p className="mt-3 font-mono text-xs text-slate-300">python -m ml.train --demo</p>
            <p className="mt-1 text-xs">Run from the backend folder. See the README for using a real dataset.</p>
          </EmptyState>
        </div>
      )}

      {info && info.available && (
        <div className="space-y-5">
          {info.dataset.is_demo_data && (
            <div role="note" className="rounded-lg border border-violet-400/30 bg-violet-400/10 p-4 text-sm text-violet-200">
              <strong>Demo sample data.</strong> {info.dataset.note} These numbers show that the pipeline works; they say nothing
              about real-world accuracy.
            </div>
          )}

          <section className="card card-pad">
            <h2 className="section-title mb-3">Training run</h2>
            <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
              <div><dt className="inline text-slate-400">Model: </dt><dd className="inline text-slate-100">{info.model_type}</dd></div>
              <div><dt className="inline text-slate-400">Trained: </dt><dd className="inline text-slate-100">{info.trained_at}</dd></div>
              <div><dt className="inline text-slate-400">Dataset: </dt><dd className="inline text-slate-100">{info.dataset.name}</dd></div>
              <div><dt className="inline text-slate-400">Rows: </dt><dd className="inline text-slate-100">{info.dataset.rows_used} ({info.dataset.phishing_rows} phishing / {info.dataset.benign_rows} benign)</dd></div>
              <div><dt className="inline text-slate-400">Split: </dt><dd className="inline text-slate-100">{info.split.method}</dd></div>
              <div><dt className="inline text-slate-400">Train/test: </dt><dd className="inline text-slate-100">{info.split.train_rows}/{info.split.test_rows} rows, {info.split.train_domains}/{info.split.test_domains} domains</dd></div>
              <div><dt className="inline text-slate-400">Cross-validation: </dt><dd className="inline text-slate-100">F1 {info.cross_validation.f1_mean.toFixed(3)} ± {info.cross_validation.f1_std.toFixed(3)}</dd></div>
              <div><dt className="inline text-slate-400">scikit-learn: </dt><dd className="inline text-slate-100">{info.sklearn_version}</dd></div>
            </dl>
            <p className="mt-3 break-all text-xs text-slate-500">Source: {info.dataset.source}</p>
          </section>

          <MetricsBlock title="Logistic regression (the model used for scoring)" m={info.metrics.logistic_regression} />
          <MetricsBlock title="Random forest (baseline for comparison)" m={info.metrics.random_forest_baseline} />

          <section className="card card-pad">
            <h2 className="section-title mb-2">Feature weights (logistic regression)</h2>
            <p className="mb-3 text-xs text-slate-500">Positive coefficients push toward "phishing-like"; negative toward "benign-like".</p>
            <div style={{ height: Math.max(220, info.feature_importance.length * 26) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={info.feature_importance} layout="vertical" margin={{ left: 40, right: 12 }}>
                  <CartesianGrid stroke="#18284a" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis type="category" dataKey="label" width={170} tick={{ fill: '#cbd5e1', fontSize: 11 }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(34,211,238,0.06)' }} />
                  <Bar dataKey="coefficient" fill="#22d3ee" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="card card-pad">
            <h2 className="section-title mb-3">Limitations</h2>
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-400">
              {info.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
            <p className="mt-3 break-all font-mono text-[11px] text-slate-600">model sha256: {info.model_sha256}</p>
          </section>
        </div>
      )}
    </>
  );
}
