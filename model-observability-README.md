# Model Observability & Drift Detection Dashboard

**CI status: verified.** The GitHub Actions pipeline (test + Azure
OIDC login + drift-check job) runs green — see
[`docs/incidents.md`](docs/incidents.md) for the two-step Azure OIDC
setup this required, now confirmed as a repeatable pattern across the
third repo in this portfolio to need it.

The fourth project in this MLOps portfolio, addressing the highest-demand
gap identified against the reference project list: monitoring,
observability, and drift-triggered retraining. Ties Projects 1 and 2
together into a closed loop — in principle. See the honest gap section
below before assuming this is fully wired end to end.

- **[Log Anomaly Detection Platform](https://github.com/sugarhillconsultants/log-anomaly-platform)** →
  source of live telemetry (volume, latency) and the model being monitored
- **[Reproducible Fine-Tuning Pipeline](https://github.com/sugarhillconsultants/reproducible-finetuning-pipeline)** →
  target of the retraining trigger when drift exceeds threshold

Full integration details, including a genuinely significant unresolved
gap stated plainly: [`docs/architecture.md`](docs/architecture.md).

## What's actually in this repo

| Path | What it does | Verified? |
|---|---|---|
| `drift/psi.py` | Population Stability Index drift detection | **Yes** — tested against known statistical scenarios (identical/shifted/variance-changed distributions), correctly detects each |
| `drift/baseline_builder.py` | Generates the baseline distribution from Project 1's actual training feature generator | **Yes** — run directly, produces a real, correctly-shaped baseline file |
| `retrain_trigger/trigger_retrain.py` | Fires `repository_dispatch` on Project 2 when drift exceeds threshold | Gating logic verified correct at the boundary; the actual GitHub API call is unverified (no network in development) |
| `dashboard/app.py` | Streamlit dashboard: volume, latency, drift | Syntactically valid, correct logic; **not yet run against live Streamlit/Azure** |
| `.github/workflows/monitor.yml` | Scheduled (every 6h) drift check + retrain trigger | YAML valid; **the drift-check step is a labeled placeholder**, not real yet — see below |
| `tests/test_psi.py` | Formal pytest suite mirroring the manually-verified PSI scenarios | Written to match verified behavior; not run via pytest itself (not installed in dev sandbox) |
| `docs/architecture.md` | Full integration details and the honest gap | — |

## The most important thing to know before using this

**The drift detection engine is real and verified. The live data feeding it is not wired up yet.**

Project 1's database doesn't currently store the raw input features
used for each prediction — only the resulting label and confidence.
Without that, there's no real "current" distribution for `psi.py` to
compare against for the features that actually matter most (the ones
the model was trained on), only for confidence scores. The dashboard
and the scheduled workflow both say this explicitly rather than faking
it with synthetic data dressed up as live telemetry — see
[`docs/architecture.md`](docs/architecture.md) for exactly what's
needed to close this gap, and why it's deliberately left open rather
than papered over.

## Why this scopes the metrics the way it does

The reference project this was built against ("Enterprise LLM
Monitoring Dashboard") lists hallucination rate and token cost as
example metrics — those are generative-LLM-specific and genuinely
don't apply to Project 1's model, which is a classifier, not a
generative LLM. This dashboard tracks what's actually meaningful for a
classifier instead: request volume, latency, and feature/prediction
drift via PSI. Forcing hallucination-rate tracking onto a
classification model would be metric theater, not real monitoring.

## Running it yourself

```bash
# Build the baseline (verified working)
python drift/baseline_builder.py --output drift/baseline.json

# Run the dashboard (needs LOG_ANALYTICS_WORKSPACE_ID for live data;
# degrades to a clear "no data" state without it, rather than crashing)
cd dashboard
pip install -r requirements.txt
LOG_ANALYTICS_WORKSPACE_ID=<Project 1's workspace GUID> streamlit run app.py

# Test the retraining trigger's gating logic manually (dry run, no real token)
python retrain_trigger/trigger_retrain.py --psi-score 0.31 --threshold 0.25 \
    --github-token <token> --target-repo sugarhillconsultants/reproducible-finetuning-pipeline
```

## What I'd add next (the real, prioritized list)

1. **Close the honest gap** — add feature logging to Project 1's
   database, replace `monitor.yml`'s placeholder step with a real
   query, wire `dashboard/app.py`'s `current_features=None` to actual data.
2. Add `repository_dispatch` handling to Project 2's own workflow, so
   the trigger this project fires actually has something listening on
   the other end.
3. Run the actual dashboard against live Streamlit + Azure infrastructure
   and document what breaks, the same way the other three projects did —
   this repo has not yet been through that process.
