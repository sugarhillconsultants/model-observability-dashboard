"""
drift/psi.py

Population Stability Index (PSI) — the standard metric for detecting
distribution drift between a baseline (training-time) population and
current (live production) traffic.

PSI < 0.10  : no significant change
0.10-0.25   : moderate change, worth investigating
PSI > 0.25  : significant change, model likely needs retraining

Works on any single numeric feature. For this project, applied to the
model's confidence scores and to each of the four input features
(is_off_hours, is_sensitive_event, is_root, error_rate) independently.
"""

import numpy as np


def compute_psi(baseline: np.ndarray, current: np.ndarray, buckets: int = 10) -> float:
    """
    Computes PSI between a baseline distribution and a current one.

    Bucket edges are derived from the BASELINE's quantiles (standard
    practice) so bucketing reflects what "normal" looked like at
    training time, not whatever the current data happens to look like.
    """
    baseline = np.asarray(baseline, dtype=float)
    current = np.asarray(current, dtype=float)

    if len(baseline) == 0 or len(current) == 0:
        raise ValueError("Both baseline and current arrays must be non-empty")

    # Quantile-based bucket edges from the baseline distribution
    quantiles = np.linspace(0, 100, buckets + 1)
    bucket_edges = np.percentile(baseline, quantiles)
    bucket_edges[0] = -np.inf
    bucket_edges[-1] = np.inf
    # Guard against degenerate (duplicate) edges when baseline has low variance
    bucket_edges = np.unique(bucket_edges)
    if len(bucket_edges) < 2:
        # Baseline has (near-)zero variance — can't meaningfully bucket
        return 0.0

    baseline_counts, _ = np.histogram(baseline, bins=bucket_edges)
    current_counts, _ = np.histogram(current, bins=bucket_edges)

    baseline_pct = baseline_counts / len(baseline)
    current_pct = current_counts / len(current)

    # Avoid division by zero / log(0) for empty buckets — floor at a
    # small epsilon, standard practice for PSI calculations
    epsilon = 1e-4
    baseline_pct = np.where(baseline_pct == 0, epsilon, baseline_pct)
    current_pct = np.where(current_pct == 0, epsilon, current_pct)

    psi_per_bucket = (current_pct - baseline_pct) * np.log(current_pct / baseline_pct)
    return float(np.sum(psi_per_bucket))


def interpret_psi(psi_value: float) -> str:
    if psi_value < 0.10:
        return "no significant drift"
    elif psi_value < 0.25:
        return "moderate drift — investigate"
    else:
        return "significant drift — retraining recommended"


def compute_feature_drift_report(baseline_df, current_df, feature_columns: list[str]) -> dict:
    """Computes PSI for multiple features at once, returning a report dict.
    baseline_df / current_df are expected to support column access like
    a pandas DataFrame or dict-of-arrays (duck-typed, no pandas required
    at this layer)."""
    report = {}
    for col in feature_columns:
        psi_value = compute_psi(baseline_df[col], current_df[col])
        report[col] = {
            "psi": round(psi_value, 4),
            "interpretation": interpret_psi(psi_value),
        }
    return report
