"""Shared risk vocabulary: severities, categories and score thresholds.

Keeping the thresholds in one place means the UI, reports and tests all agree.
"""
from __future__ import annotations

from typing import Literal

Severity = Literal["info", "low", "medium", "high"]
RiskCategory = Literal["low", "suspicious", "high"]
InputType = Literal["url", "email"]

# score < SUSPICIOUS_THRESHOLD            -> "low"
# SUSPICIOUS_THRESHOLD <= score < HIGH    -> "suspicious"
# score >= HIGH_THRESHOLD                 -> "high"
SUSPICIOUS_THRESHOLD = 20
HIGH_THRESHOLD = 50

# ML scores >= this are labelled "phishing-like" (0.5 on the model's 0-1 output).
ML_FLAG_THRESHOLD = 50


def categorize(score: int) -> RiskCategory:
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= SUSPICIOUS_THRESHOLD:
        return "suspicious"
    return "low"
