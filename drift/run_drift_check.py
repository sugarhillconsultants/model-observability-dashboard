"""
drift/run_drift_check.py

Replaces the hardcoded psi_score=0.0 placeholder in monitor.yml with a
real check: authenticates to Project 1's live API, fetches real recent
prediction data, computes actual PSI against the stored baseline, and
prints a GitHub Actions output the workflow can gate the retrain
trigger on.

Install once:
  pip install requests numpy

Usage:
  python run_drift_check.py --api-url https://ca-log-anomaly.<...>.azurecontainerapps.io \
      --username analyst --password $DEMO_PASSWORD --baseline baseline.json
"""

import argparse
import json
import sys
import requests

sys.path.insert(0, ".")
from drift.psi import compute_psi


def get_auth_token(api_url: str, username: str, password: str) -> str:
    response = requests.post(f"{api_url}/token", data={"username": username, "password": password}, timeout=15)
    response.raise_for_status()
    return response.json()["access_token"]


def get_recent_features(api_url: str, token: str, limit: int = 500) -> dict:
    response = requests.get(
        f"{api_url}/events/recent-features",
        params={"limit": limit},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main(api_url: str, username: str, password: str, baseline_path: str):
    with open(baseline_path) as f:
        baseline = json.load(f)

    token = get_auth_token(api_url, username, password)
    current = get_recent_features(api_url, token)

    if current["n"] < 20:
        print(f"Only {current['n']} live events available — not enough for a "
              f"meaningful drift comparison yet. Reporting PSI=0.0 (no action) "
              f"rather than a noisy score from too small a sample.")
        psi_score = 0.0
    else:
        psi_confidence = compute_psi(baseline["confidence"], current["confidence"])
        psi_length = compute_psi(baseline["text_length"], current["text_length"])
        psi_score = max(psi_confidence, psi_length)
        print(f"PSI (confidence): {psi_confidence:.4f}")
        print(f"PSI (text_length): {psi_length:.4f}")
        print(f"Reporting max: {psi_score:.4f}")

    # GitHub Actions output, consumed by monitor.yml's retrain-trigger step
    import os
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"psi_score={psi_score}\n")

    return psi_score


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--baseline", default="baseline.json")
    args = parser.parse_args()
    main(args.api_url, args.username, args.password, args.baseline)
