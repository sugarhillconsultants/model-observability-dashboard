"""
retrain_trigger/trigger_retrain.py

Closes the loop between this observability project and Project 2
(Reproducible Fine-Tuning Pipeline): when drift exceeds threshold,
this fires a `repository_dispatch` event against Project 2's GitHub
repo, triggering its actual fine-tuning workflow — not just logging
"drift detected" and stopping there.

Install once:
  pip install requests

Usage:
  python trigger_retrain.py --psi-score 0.31 --threshold 0.25 \
      --github-token $GITHUB_TOKEN --target-repo sugarhillconsultants/reproducible-finetuning-pipeline
"""

import argparse
import sys
import requests


def trigger_retraining(github_token: str, target_repo: str, psi_score: float, drift_report: dict = None):
    """Fires a repository_dispatch event. Project 2's workflow would need
    a `repository_dispatch` trigger added (types: [retrain-on-drift]) to
    actually respond to this — see docs/architecture.md for the wiring
    still needed on that side, stated honestly rather than assumed done."""
    url = f"https://api.github.com/repos/{target_repo}/dispatches"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {
        "event_type": "retrain-on-drift",
        "client_payload": {
            "psi_score": psi_score,
            "triggered_by": "model-observability-dashboard",
            "drift_report": drift_report or {},
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 204:
        print(f"Retraining triggered successfully for {target_repo} (PSI={psi_score})")
        return True
    else:
        print(f"Failed to trigger retraining: {response.status_code} {response.text}")
        return False


def main(psi_score: float, threshold: float, github_token: str, target_repo: str):
    print(f"Current PSI: {psi_score}, threshold: {threshold}")

    if psi_score <= threshold:
        print("Drift within acceptable range — no retraining needed.")
        return 0

    print(f"Drift threshold exceeded (PSI {psi_score} > {threshold}) — triggering retraining...")
    success = trigger_retraining(github_token, target_repo, psi_score)
    return 0 if success else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--psi-score", type=float, required=True)
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--github-token", required=True)
    parser.add_argument("--target-repo", default="sugarhillconsultants/reproducible-finetuning-pipeline")
    args = parser.parse_args()

    sys.exit(main(args.psi_score, args.threshold, args.github_token, args.target_repo))
