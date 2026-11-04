import { useState, type FormEvent } from 'react';

import { ErrorBanner, PageHeader } from '../components/Feedback';
import ScanResultView from '../components/ScanResultView';
import { useToast } from '../hooks/useToast';
import { api } from '../services/api';
import type { ScanResult } from '../types/api';

// Obviously fake, defanged-style examples. They are only analyzed as text; nothing is opened.
const EXAMPLES = [
  'https://example.com/docs/getting-started',
  'http://secure-login.paypal.com.account-verify.example-test.xyz/signin?session=1',
  'http://192.168.10.20:8080/bank/login.php',
];

export default function UrlAnalyzerPage() {
  const toast = useToast();
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = url.trim();
    if (!value) {
      setError('Enter a URL to analyze.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const scan = await api.analyzeUrl(value);
      setResult(scan);
      toast.push('success', `Analysis complete: ${scan.risk_score}/100.`);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : 'Analysis failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="URL Analyzer"
        subtitle="Paste a suspicious link. It is inspected as text only: PhishGuard never opens it, fetches it or follows redirects."
      />
      <form onSubmit={onSubmit} className="card card-pad mb-5" noValidate>
        <label htmlFor="url-input" className="label">
          URL to analyze
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="url-input"
            className="input font-mono"
            type="text"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            placeholder="https://example.com/path"
            value={url}
            maxLength={2048}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button type="submit" className="btn-primary sm:w-40" disabled={busy}>
            {busy ? 'Analyzing…' : 'Analyze URL'}
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Try an example:{' '}
          {EXAMPLES.map((ex, i) => (
            <button
              key={ex}
              type="button"
              className="mr-2 rounded px-1 text-accent underline-offset-2 hover:underline"
              onClick={() => setUrl(ex)}
            >
              example {i + 1}
            </button>
          ))}
        </p>
      </form>
      {error && <ErrorBanner message={error} />}
      {result && (
        <div className="mt-5">
          <ScanResultView scan={result} />
        </div>
      )}
    </>
  );
}
