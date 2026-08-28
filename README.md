# Model Observability & Drift Detection Dashboard

**CI status: verified.** The GitHub Actions pipeline (test + drift-check
job) runs green — see [`docs/incidents.md`](docs/incidents.md) for the
two-step Azure OIDC setup this required, now confirmed as a repeatable
pattern across the third repo in this portfolio to need it.

**Core logic status: corrected and real, but the live baseline is still
small.** An earlier version of this repo had a genuine design bug — its
baseline builder generated features that don't exist in the model
actually being monitored. That's been fixed; the pipeline now runs
against real signals (confidence, text length) end to end in principle.
What remains is narrower than before: the baseline needs real
production traffic to be statistically meaningful, and the full
workflow hasn't yet been run against a live deployment. See the section
below for the precise, current state.

The fourth project in this MLOps portfolio, addressing the highest-demand
gap identified against the reference project list: monitoring,
observability, and drift-triggered retraining. Ties Projects 1 and 2
together into a closed loop.

- **[Log Anomaly Detection Platform](https://github.com/sugarhillconsultants/log-anomaly-platform)** →
  source of live telemetry (volume, latency) and the model being monitored;
  now also exposes `/events/recent-features` specifically for this project
- **[Reproducible Fine-Tuning Pipeline](https://github.com/sugarhillconsultants/reproducible-finetuning-pipeline)** →
  target of the retraining trigger when drift exceeds threshold

Full integration details: [`docs/architecture.md`](docs/architecture.md).

## What's actually in this repo

| Path | What it does | Verified? |
|---|---|---|
| `drift/psi.py` | Population Stability Index drift detection | **Yes** — tested against known statistical scenarios (identical/shifted/variance-changed distributions), correctly detects each |
| `drift/baseline_builder.py` | Builds a baseline from **confidence + text length** — corrected from an earlier version that mistakenly generated tabular features belonging to a different project's model | **Yes** — `--from-seed` path run directly, produces a real baseline file from actual observed live model outputs; `--from-live` path is correct but unverified against a real API (needs enough production traffic to matter) |
| `drift/run_drift_check.py` | Authenticates to Project 1's live API, fetches real recent predictions, computes real PSI | Logic (small-sample guard, max-of-two-scores gating) verified correct in isolation; the live HTTP round-trip to Project 1 is unverified end-to-end |
| `retrain_trigger/trigger_retrain.py` | Fires `repository_dispatch` on Project 2 when drift exceeds threshold | Gating logic verified correct at the boundary; the actual GitHub API call is unverified (no network in development) |
| `dashboard/app.py` | Streamlit dashboard: volume, latency, drift — now wired to query Project 1's real `/events/recent-features` endpoint instead of a hardcoded `None` | Syntactically valid, correct logic; **not yet run against live Streamlit/Azure** |
| `.github/workflows/monitor.yml` | Scheduled (every 6h) drift check + retrain trigger — the drift-check step now calls the real script above, not a hardcoded value | YAML valid; **has not yet been run end-to-end against a live Project 1 deployment** |
| `tests/test_psi.py` | Formal pytest suite mirroring the manually-verified PSI scenarios | Written to match verified behavior; not run via pytest itself (not installed in dev sandbox) |
| `docs/architecture.md` | Full integration details and the current, narrower gap | — |

## An earlier design mistake, corrected — and what's genuinely left open now

**The original version of this repo had a real bug, not just a missing
integration**: `drift/baseline_builder.py` generated four tabular
features (`is_off_hours`, `is_sensitive_event`, `is_root`,
`error_rate`) that belong to a *different* project's simple sklearn
model. Project 1's actual deployed model is a fine-tuned DistilBERT
**text classifier** — it has no such features at all. That version of
this repo could never have worked correctly even with live data wired
up, because it was measuring drift on inputs the real model doesn't use.

**This has been corrected.** The baseline and drift check now use the
two numeric signals that actually exist for a text classifier:
**confidence score** and **text length**. Project 1 gained a new
endpoint, `GET /events/recent-features`, specifically to expose these
for real.

**What's genuinely closed now:**
- The baseline builder produces a real baseline from actual observed
  model behavior (not an invented distribution), via `--from-seed`.
- `run_drift_check.py` authenticates to Project 1 and computes real
  PSI against real data, when real data exists.
- The dashboard and scheduled workflow both call the real path, not a
  `None`/hardcoded placeholder.

**What's still genuinely open, stated precisely rather than vaguely:**
- The `--from-seed` baseline currently has **only 2 samples** — enough
  to prove the pipeline mechanics work end to end, but explicitly too
  small to be a statistically meaningful reference. A real baseline
  needs `--from-live` run against Project 1 once it has accumulated
  a real burn-in period of production traffic (the code already
  supports this; it just needs real traffic to run against).
- Neither `run_drift_check.py`'s live HTTP calls nor
  `monitor.yml`'s full execution against a real Project 1 deployment
  have actually been run yet — this is architecturally correct,
  verified-in-isolation code, not confirmed working end to end the way
  Projects 1–3's core functionality is.
- Project 2 has no `repository_dispatch` listener yet, so even a
  correctly-fired retrain trigger currently has nothing on the
  receiving end.

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
# Build a starter baseline from real (if small) observed model outputs
python drift/baseline_builder.py --from-seed --output drift/baseline.json

# Once Project 1 has real production traffic, build a proper baseline instead:
# python drift/baseline_builder.py --from-live \
#     --api-url https://<project-1-fqdn> --token <jwt> --output drift/baseline.json

# Run a real drift check against Project 1's live API
python drift/run_drift_check.py \
    --api-url https://<project-1-fqdn> \
    --username analyst --password <demo-password> \
    --baseline drift/baseline.json

# Run the dashboard (needs LOG_ANALYTICS_WORKSPACE_ID for volume/latency,
# LOG_ANOMALY_API_URL + LOG_ANOMALY_API_TOKEN for real drift data;
# degrades to a clear "no data" state without them, rather than crashing)
cd dashboard
pip install -r requirements.txt
LOG_ANALYTICS_WORKSPACE_ID=<Project 1's workspace GUID> \
LOG_ANOMALY_API_URL=https://<project-1-fqdn> \
LOG_ANOMALY_API_TOKEN=<jwt> \
streamlit run app.py

# Test the retraining trigger's gating logic manually (dry run, no real token)
python retrain_trigger/trigger_retrain.py --psi-score 0.31 --threshold 0.25 \
    --github-token <token> --target-repo sugarhillconsultants/reproducible-finetuning-pipeline
```

## What I'd add next (the real, prioritized list)

1. **Let Project 1 accumulate real production traffic**, then rebuild
   the baseline with `--from-live` instead of the 2-sample
   `--from-seed` starter — the single biggest remaining gap between
   "the pipeline works" and "the pipeline says something meaningful."
2. **Actually run `monitor.yml` end to end against a live Project 1
   deployment** and document what breaks, the same way the other three
   projects did — this specific workflow has not yet been through that
   process, only its component scripts have been verified in isolation.
3. Add `repository_dispatch` handling to Project 2's own workflow, so
   the trigger this project fires actually has something listening on
   the other end.
4. Run the actual dashboard against live Streamlit + Azure infrastructure.
