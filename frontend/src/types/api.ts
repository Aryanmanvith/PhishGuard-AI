// TypeScript mirror of backend/app/schemas/scan.py. Keep the two files in sync.

export type RiskCategory = 'low' | 'suspicious' | 'high';
export type Severity = 'info' | 'low' | 'medium' | 'high';
export type InputType = 'url' | 'email';

export interface Indicator {
  id: string;
  title: string;
  severity: Severity;
  points: number;
  evidence: string;
  explanation: string;
}

export interface FeatureContribution {
  feature: string;
  label: string;
  value: number;
  contribution: number;
  direction: 'raises' | 'lowers';
}

export interface MLResult {
  available: boolean;
  score: number | null;
  label: 'phishing-like' | 'benign-like' | null;
  model_name: string | null;
  trained_on_demo_data: boolean | null;
  top_features: FeatureContribution[];
  note: string;
}

export interface Comparison {
  status: 'agree' | 'disagree' | 'unavailable';
  summary: string;
}

export interface Confidence {
  level: 'limited' | 'moderate';
  note: string;
}

/** Extra data for email scans (details.links). */
export interface EmailLink {
  url: string;
  host: string;
  registered_domain: string;
  risk_score: number;
  risk_category: RiskCategory;
  top_indicators: string[];
}

export interface ScanResult {
  scan_id: string;
  input_type: InputType;
  input_summary: string;
  risk_score: number;
  risk_category: RiskCategory;
  indicators: Indicator[];
  ml: MLResult | null;
  comparison: Comparison | null;
  confidence: Confidence;
  limitations: string[];
  details: Record<string, unknown>;
  analyzed_at: string;
  is_demo: boolean;
}

export interface ScanSummary {
  scan_id: string;
  input_type: InputType;
  input_summary: string;
  risk_score: number;
  risk_category: RiskCategory;
  ml_score: number | null;
  indicator_count: number;
  created_at: string;
  is_demo: boolean;
}

export interface ScanListResponse {
  items: ScanSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface DailyCount {
  date: string;
  total: number;
  high: number;
}

export interface IndicatorCount {
  id: string;
  title: string;
  count: number;
}

export interface StatsResponse {
  total_scans: number;
  by_category: Record<RiskCategory, number>;
  by_input_type: Record<InputType, number>;
  demo_scans: number;
  average_score: number;
  last_14_days: DailyCount[];
  top_indicators: IndicatorCount[];
}

export interface HealthResponse {
  status: 'ok';
  app: string;
  version: string;
  model_available: boolean;
  database_ok: boolean;
  static_analysis_only: boolean;
}

export interface EmailPayload {
  body: string;
  sender?: string;
  reply_to?: string;
  subject?: string;
}

// ------------------------------------------------------------------ model info

export interface ModelMetrics {
  threshold: number;
  n_test: number;
  precision: number;
  recall: number;
  f1: number;
  accuracy: number;
  roc_auc: number | null;
  confusion_matrix: number[][]; // [[TN, FP], [FN, TP]]
  confusion_matrix_labels: string[];
}

export interface ModelUnavailable {
  available: false;
  reason: string;
}

export interface ModelAvailable {
  available: true;
  model_type: string;
  trained_at: string;
  sklearn_version: string;
  random_state: number;
  feature_names: string[];
  dataset: {
    name: string;
    source: string;
    is_demo_data: boolean;
    rows_used: number;
    phishing_rows: number;
    benign_rows: number;
    skipped_unparseable: number;
    note: string;
  };
  split: {
    method: string;
    test_size: number;
    train_rows: number;
    test_rows: number;
    train_domains: number;
    test_domains: number;
  };
  metrics: {
    logistic_regression: ModelMetrics;
    random_forest_baseline: ModelMetrics;
  };
  cross_validation: { method: string; f1_mean: number; f1_std: number };
  feature_importance: { feature: string; label: string; coefficient: number }[];
  limitations: string[];
  model_sha256: string;
}

export type ModelInfo = ModelUnavailable | ModelAvailable;
