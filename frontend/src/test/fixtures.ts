import type { ScanResult } from '../types/api';

export const highRiskScan: ScanResult = {
  scan_id: 'a'.repeat(32),
  input_type: 'url',
  input_summary: 'http://192.168.0.1/login',
  risk_score: 82,
  risk_category: 'high',
  indicators: [
    {
      id: 'ip_host',
      title: 'Host is an IP address',
      severity: 'high',
      points: 25,
      evidence: '192.168.0.1',
      explanation: 'Legitimate services almost always use a domain name.',
    },
  ],
  ml: {
    available: false,
    score: null,
    label: null,
    model_name: null,
    trained_on_demo_data: null,
    top_features: [],
    note: 'No trained model found.',
  },
  comparison: null,
  confidence: { level: 'moderate', note: 'Several independent indicators agree.' },
  limitations: ['Static analysis cannot see page content.'],
  details: {},
  analyzed_at: '2026-10-18T04:00:00Z',
  is_demo: false,
};
