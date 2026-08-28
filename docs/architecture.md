# Architecture: How This Ties to Projects 1 and 2 — and What's Genuinely Not Wired Up Yet

## What comes from [Log Anomaly Detection Platform](https://github.com/sugarhillconsultants/log-anomaly-platform)

The traffic and telemetry this dashboard visualizes: the same
Application Insights workspace Project 1 already emits request/latency
data to (`LOG_ANALYTICS_WORKSPACE_ID`). No new instrumentation needed
on that side for volume/latency — it's already there.

## What comes from [Reproducible Fine-Tuning Pipeline](https://github.com/sugarhillconsultants/reproducible-finetuning-pipeline)

The retraining trigger's target: `retrain_trigger/trigger_retrain.py`
fires a `repository_dispatch` event against that repo when drift
crosses threshold, intended to kick off its actual fine-tuning workflow.

## What's genuinely new here

- **PSI-based drift detection** (`drift/psi.py`) — verified correct
  against known statistical scenarios (identical distributions score
  near-zero, severe shifts score high, variance-only shifts are
  detected too), not just written and assumed right.
- **A dashboard** visualizing what actually applies to a classifier —
  volume, latency, feature/prediction drift — rather than forcing
  generative-LLM metrics (token cost, hallucination rate) onto a model
  type they don't apply to.
- **A closed retraining loop**, at least architecturally: drift
  detection → threshold check → `repository_dispatch` → Project 2's
  pipeline.

## The honest, significant gap: there is no live "current" feature data yet

This is the most important thing to state plainly, consistent with
every other project in this portfolio: **PSI needs two distributions —
a baseline and a current one — and this project only has the baseline
side working for real.**

Project 1's database (`app/database.py`'s `LogEventRecord`) currently
stores `text`, `predicted_label`, and `confidence` per event — it does
**not** store the four raw input features (`is_off_hours`,
`is_sensitive_event`, `is_root`, `error_rate`) that were used to make
each prediction. Without those, there is no real "current" distribution
for `psi.py` to compare the baseline against for the *input features* —
only for `confidence`, which Project 1's schema does capture.

**What this means concretely:**
- `dashboard/app.py`'s drift section is wired correctly but passes
  `current_features=None` — it will not silently fake this as working;
  it explicitly says why the comparison isn't running yet.
- `.github/workflows/monitor.yml`'s `check-drift` step is a labeled
  placeholder that hardcodes `psi_score=0.0`, not a real query — it
  will never trigger retraining as currently committed, and says so in
  its own log output rather than pretending to function.
- The retraining trigger itself (`trigger_retrain.py`) is fully
  implemented and its gating logic is verified correct in isolation —
  it's the *input* to it (a real PSI score from real live data) that's
  the missing piece, not the trigger mechanism itself.

**What it would take to close this gap for real:**
1. Add an `input_features` JSON column to Project 1's `LogEventRecord`,
   storing the four features alongside each prediction.
2. Replace `monitor.yml`'s placeholder step with a real query against
   that column (either via Project 1's own database, or by having
   Project 1 also log features to Application Insights as custom
   dimensions on each request).
3. Compute PSI against the real baseline using `compute_feature_drift_report()`
   (already implemented and tested) instead of the hardcoded `0.0`.

This is deliberately documented as the next step rather than faked with
synthetic "current" data dressed up as live telemetry — doing that
would misrepresent a demo as a working system, which is exactly the
kind of gap this whole portfolio's incident logs argue against papering
over.
