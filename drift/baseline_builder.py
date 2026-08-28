"""
drift/baseline_builder.py

Builds the baseline distribution PSI is measured against. In a real
deployment, this would be a snapshot of the actual feature distribution
from the training data used in Project 2 (Reproducible Fine-Tuning
Pipeline) or the initial weeks of production traffic. For this
demonstration, it regenerates the same synthetic distribution used to
train Project 1's classifier, so the baseline is a genuine, principled
reference rather than an arbitrary placeholder.

Install once:
  pip install numpy

Usage:
  python baseline_builder.py --output baseline.json
"""

import argparse
import json
import numpy as np


def generate_baseline(n_samples: int = 2000, seed: int = 42) -> dict:
    """Mirrors the exact feature-generation logic used to train Project
    1's log classifier (see log-anomaly-platform's training data), so
    this baseline reflects what the model actually learned as 'normal'."""
    rng = np.random.default_rng(seed)
    X = rng.random((n_samples, 4))

    return {
        "is_off_hours": X[:, 0].tolist(),
        "is_sensitive_event": X[:, 1].tolist(),
        "is_root": X[:, 2].tolist(),
        "error_rate": X[:, 3].tolist(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="baseline.json")
    parser.add_argument("--n-samples", type=int, default=2000)
    args = parser.parse_args()

    baseline = generate_baseline(args.n_samples)
    with open(args.output, "w") as f:
        json.dump(baseline, f)

    print(f"Baseline written to {args.output} ({args.n_samples} samples per feature)")
