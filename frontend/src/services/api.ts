import type {
  EmailPayload,
  HealthResponse,
  ModelInfo,
  ScanListResponse,
  ScanResult,
  StatsResponse,
} from '../types/api';

// In development BASE is '' and Vite proxies /api -> http://127.0.0.1:8000.
const BASE: string = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '').replace(/\/$/, '');

/** An error we can show to the user as-is. `code` matches the backend's error envelope. */
export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

async function rawRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (init.body) headers['Content-Type'] = 'application/json';

  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      'Cannot reach the PhishGuard backend. Make sure it is running (run.bat) and try again.',
      0,
      'network_error',
    );
  }

  if (!res.ok) {
    let message = `Request failed (HTTP ${res.status}).`;
    let code = 'http_error';
    try {
      const body = (await res.json()) as { error?: { code?: string; message?: string } };
      if (body.error?.message) message = body.error.message;
      if (body.error?.code) code = body.error.code;
    } catch {
      // Response was not JSON; keep the generic message.
    }
    throw new ApiError(message, res.status, code);
  }
  return res;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await rawRequest(path, init);
  return (await res.json()) as T;
}

/** Fetch a file from the API and hand it to the browser as a download. */
async function download(path: string, fallbackName: string): Promise<void> {
  const res = await rawRequest(path);
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition') ?? '';
  const match = /filename="?([^";]+)"?/.exec(disposition);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = match?.[1] ?? fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export interface ListParams {
  limit?: number;
  offset?: number;
  category?: string;
  inputType?: string;
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  analyzeUrl: (url: string) =>
    request<ScanResult>('/analyze/url', { method: 'POST', body: JSON.stringify({ url }) }),

  analyzeEmail: (payload: EmailPayload) =>
    request<ScanResult>('/analyze/email', { method: 'POST', body: JSON.stringify(payload) }),

  listScans: ({ limit = 20, offset = 0, category, inputType }: ListParams = {}) => {
    const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (category) q.set('category', category);
    if (inputType) q.set('input_type', inputType);
    return request<ScanListResponse>(`/scans?${q.toString()}`);
  },

  getScan: (id: string) => request<ScanResult>(`/scans/${encodeURIComponent(id)}`),

  clearScans: (demoOnly = false) =>
    request<{ deleted: number }>(`/scans?confirm=true${demoOnly ? '&demo_only=true' : ''}`, {
      method: 'DELETE',
    }),

  stats: () => request<StatsResponse>('/stats'),

  model: () => request<ModelInfo>('/model'),

  seedDemo: () => request<{ inserted: number; note: string }>('/demo/seed', { method: 'POST' }),

  downloadScanReport: (id: string) =>
    download(`/scans/${encodeURIComponent(id)}/report.json`, `phishguard-report-${id.slice(0, 8)}.json`),

  downloadHistoryCsv: () => download('/reports/history.csv', 'phishguard-history.csv'),
};
