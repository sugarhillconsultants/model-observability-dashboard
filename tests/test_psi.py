"""
tests/test_psi.py

Formal test suite for the PSI engine, covering the same scenarios
verified manually during development, so CI catches any regression.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "drift"))
from psi import compute_psi, interpret_psi, compute_feature_drift_report


def test_identical_distributions_score_near_zero():
    rng = np.random.default_rng(42)
    baseline = rng.normal(0.5, 0.15, 5000)
    current = rng.normal(0.5, 0.15, 5000)
    psi = compute_psi(baseline, current)
    assert psi < 0.10


def test_severe_mean_shift_scores_high():
    rng = np.random.default_rng(42)
    baseline = rng.normal(0.5, 0.15, 5000)
    current = rng.normal(0.9, 0.15, 5000)
    psi = compute_psi(baseline, current)
    assert psi > 0.25


def test_variance_only_shift_is_detected():
    rng = np.random.default_rng(42)
    baseline = rng.normal(0.5, 0.15, 5000)
    current = rng.normal(0.5, 0.35, 5000)  # same mean, wider spread
    psi = compute_psi(baseline, current)
    assert psi > 0.10


def test_empty_array_raises():
    import pytest
    with pytest.raises(ValueError):
        compute_psi(np.array([]), np.array([0.5]))


def test_interpret_psi_bands():
    assert interpret_psi(0.05) == "no significant drift"
    assert interpret_psi(0.15) == "moderate drift — investigate"
    assert interpret_psi(0.30) == "significant drift — retraining recommended"


def test_feature_drift_report_covers_all_columns():
    rng = np.random.default_rng(42)
    baseline = {
        "is_off_hours": rng.random(1000),
        "confidence": rng.normal(0.85, 0.1, 1000),
    }
    current = {
        "is_off_hours": rng.random(1000),
        "confidence": rng.normal(0.85, 0.1, 1000),
    }
    report = compute_feature_drift_report(baseline, current, ["is_off_hours", "confidence"])
    assert set(report.keys()) == {"is_off_hours", "confidence"}
    for col_report in report.values():
        assert "psi" in col_report
        assert "interpretation" in col_report
