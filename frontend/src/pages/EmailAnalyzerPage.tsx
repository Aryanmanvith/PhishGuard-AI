import { useState, type FormEvent } from 'react';

import { ErrorBanner, PageHeader } from '../components/Feedback';
import ScanResultView from '../components/ScanResultView';
import { useToast } from '../hooks/useToast';
import { api } from '../services/api';
import type { EmailPayload, ScanResult } from '../types/api';

const SAMPLE = {
  sender: 'PayPal Support <service@paypa1-security.example>',
  subject: 'Urgent: your account will be suspended',
  body: 'Dear customer,\n\nWe noticed unusual activity. Your account will be suspended within 24 hours unless you verify your password and card details immediately:\n\nhttp://paypa1-security.example/verify/login\n\nThank you,\nSecurity Team',
};

export default function EmailAnalyzerPage() {
  const toast = useToast();
  const [sender, setSender] = useState('');
  const [replyTo, setReplyTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) {
      setError('Paste the email text to analyze.');
      return;
    }
    const payload: EmailPayload = { body: body.trim() };
    if (sender.trim()) payload.sender = sender.trim();
    if (replyTo.trim()) payload.reply_to = replyTo.trim();
    if (subject.trim()) payload.subject = subject.trim();

    setBusy(true);
    setError(null);
    try {
      const scan = await api.analyzeEmail(payload);
      setResult(scan);
      toast.push('success', `Analysis complete: ${scan.risk_score}/100.`);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : 'Analysis failed.');
    } finally {
      setBusy(false);
    }
  }

  function loadSample() {
    setSender(SAMPLE.sender);
    setSubject(SAMPLE.subject);
    setBody(SAMPLE.body);
    setReplyTo('');
  }

  return (
    <>
      <PageHeader
        title="Email Analyzer"
        subtitle="Paste an email to check wording, links and sender consistency. Processing happens on your machine; the raw email text is not saved or sent anywhere."
        actions={
          <button type="button" className="btn-secondary" onClick={loadSample}>
            Load fake sample
          </button>
        }
      />
      <form onSubmit={onSubmit} className="card card-pad mb-5 space-y-4" noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="email-sender" className="label">
              Sender (optional)
            </label>
            <input id="email-sender" className="input" placeholder='Name <user@example.com>' value={sender} maxLength={400} onChange={(e) => setSender(e.target.value)} />
          </div>
          <div>
            <label htmlFor="email-reply" className="label">
              Reply-To (optional)
            </label>
            <input id="email-reply" className="input" placeholder="reply@example.com" value={replyTo} maxLength={400} onChange={(e) => setReplyTo(e.target.value)} />
          </div>
        </div>
        <div>
          <label htmlFor="email-subject" className="label">
            Subject (optional)
          </label>
          <input id="email-subject" className="input" value={subject} maxLength={500} onChange={(e) => setSubject(e.target.value)} />
        </div>
        <div>
          <label htmlFor="email-body" className="label">
            Email text
          </label>
          <textarea
            id="email-body"
            className="input min-h-[200px] font-mono"
            placeholder="Paste the full message body here…"
            value={body}
            maxLength={20000}
            onChange={(e) => setBody(e.target.value)}
          />
          <p className="mt-1 text-xs text-slate-500">{body.length.toLocaleString()} / 20,000 characters</p>
        </div>
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? 'Analyzing…' : 'Analyze email'}
        </button>
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
