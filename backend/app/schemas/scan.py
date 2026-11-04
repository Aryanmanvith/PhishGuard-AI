"""Pydantic schemas: the exact JSON shapes the API accepts and returns.

The frontend mirrors these in frontend/src/types/api.ts. If you change a
field here, change it there too.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.risk import InputType, RiskCategory, Severity

# ----------------------------------------------------------------- requests


class UrlRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(min_length=1, max_length=2048, description="http(s) URL to analyze statically.")


class EmailRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    body: str = Field(min_length=1, max_length=20_000, description="Pasted email text (plain or HTML).")
    sender: str | None = Field(default=None, max_length=400, description='e.g. "Name <user@example.com>"')
    reply_to: str | None = Field(default=None, max_length=400)
    subject: str | None = Field(default=None, max_length=500)


# ----------------------------------------------------------------- results


class Indicator(BaseModel):
    id: str
    title: str
    severity: Severity
    points: int = Field(ge=0, description="Points this indicator added to the heuristic score.")
    evidence: str = Field(description="The concrete thing we saw (a hostname, a phrase, a port...).")
    explanation: str = Field(description="Why this matters, in plain language.")


class FeatureContribution(BaseModel):
    feature: str
    label: str
    value: float
    contribution: float = Field(description="coefficient x standardized value (log-odds units).")
    direction: Literal["raises", "lowers"]


class MLResult(BaseModel):
    available: bool
    score: float | None = Field(default=None, description="Model output x100. NOT a calibrated probability.")
    label: Literal["phishing-like", "benign-like"] | None = None
    model_name: str | None = None
    trained_on_demo_data: bool | None = None
    top_features: list[FeatureContribution] = []
    note: str


class Comparison(BaseModel):
    status: Literal["agree", "disagree", "unavailable"]
    summary: str


class Confidence(BaseModel):
    level: Literal["limited", "moderate"]
    note: str


class ScanResult(BaseModel):
    scan_id: str
    input_type: InputType
    input_summary: str
    risk_score: int = Field(ge=0, le=100, description="Heuristic score. NOT a probability.")
    risk_category: RiskCategory
    indicators: list[Indicator]
    ml: MLResult | None = None
    comparison: Comparison | None = None
    confidence: Confidence
    limitations: list[str]
    details: dict[str, Any] = Field(default_factory=dict)
    analyzed_at: str
    is_demo: bool = False


class ScanSummary(BaseModel):
    scan_id: str
    input_type: InputType
    input_summary: str
    risk_score: int
    risk_category: RiskCategory
    ml_score: float | None
    indicator_count: int
    created_at: str
    is_demo: bool


class ScanListResponse(BaseModel):
    items: list[ScanSummary]
    total: int
    limit: int
    offset: int


# ----------------------------------------------------------------- stats


class DailyCount(BaseModel):
    date: str
    total: int
    high: int


class IndicatorCount(BaseModel):
    id: str
    title: str
    count: int


class StatsResponse(BaseModel):
    total_scans: int
    by_category: dict[str, int]
    by_input_type: dict[str, int]
    demo_scans: int
    average_score: float
    last_14_days: list[DailyCount]
    top_indicators: list[IndicatorCount]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    version: str
    model_available: bool
    database_ok: bool
    static_analysis_only: bool = True


class ClearResponse(BaseModel):
    deleted: int


class SeedResponse(BaseModel):
    inserted: int
    note: str
