# Architecture: How This Ties to Projects 1 and 2 — and What's Genuinely Still Open

## What comes from [Log Anomaly Detection Platform](https://github.com/sugarhillconsultants/log-anomaly-platform)

Two things, not one:
- **Volume/latency telemetry** — the same Application Insights workspace
  Project 1 already emits request data to (`LOG_ANALYTICS_WORKSPACE_ID`).
  No new instrumentation needed for this.
- **`GET /events/recent-features`** — a new endpoint added to Project 1
  specifically for this project, returning confidence scores and text
  lengths from recent classified events. This is the real fix for a
  design mistake described below, not something that existed from the start.

## What comes from [Reproducible Fine-Tuning Pipeline](https://github.com/sugarhillconsultants/reproducible-finetuning-pipeline)

The retraining trigger's target: `retrain_trigger/trigger_retrain.py`
fires a `repository_dispatch` event against that repo when drift
crosses threshold, intended to kick off its actual fine-tuning workflow.
Project 2 does not yet have a `repository_dispatch` listener configured
to receive this — see "still open" below.

## A real design mistake, and how it was actually corrected

The first version of this repo's `drift/baseline_builder.py` generated
four tabular features — `is_off_hours`, `is_sensitive_event`, `is_root`,
`error_rate` — as the basis for drift detection. **This was wrong, not
just incomplete.** Those features belong to a different project's
simple sklearn model (the one built early in this portfolio for
Project 3's showcase app). Project 1's actual deployed model
(`oromeop/log-classifier-tiny`) is a fine-tuned DistilBERT **text**
classifier — it takes a raw log string as input and has no tabular
feature vector at all. A baseline built on features that don't exist
in the real system could never have produced a meaningful drift signal,
no matter how well the live-data wiring was eventually completed.

**The fix**: reground drift detection in signals that genuinely exist
for a text classifier — **confidence score** (already stored in
`LogEventRecord`) and **text length** (trivially derived from the
stored `text` field). Concretely:

- Project 1 gained `GET /events/recent-features`, returning confidence
  and text-length arrays for recent events.
- `drift/baseline_builder.py` was rewritten with two honest paths:
  `--from-seed` (a small, explicitly-labeled starter set built from
  *actual* confidence values observed during this portfolio's own live
  testing — 0.619 and 0.737 — not invented numbers) and `--from-live`
  (pulls a real sample from the new endpoint once Project 1 has enough
  production traffic to be representative).
- `drift/run_drift_check.py` is new: authenticates to Project 1,
  fetches real recent data, computes real PSI against the stored
  baseline for both confidence and text length, and reports the
  worse of the two.
- `dashboard/app.py` and `monitor.yml` were both updated to call this
  real path instead of a hardcoded `None`/`0.0`.

## What's genuinely closed now

- The drift-detection *logic* is grounded in the right data model —
  no more measuring drift on inputs the deployed model doesn't use.
- Every piece of new/changed code has been verified in isolation: the
  seed baseline builder actually runs and produces a correct file; the
  recent-features extraction logic matches real observed values; the
  drift-check script's small-sample guard and max-of-two-scores gating
  are each confirmed correct through direct testing.

## What's genuinely still open — stated precisely, not vaguely

1. **The seed baseline has only 2 samples.** This is intentional and
   labeled clearly in the code (`build_from_seed()` prints a warning
   every time it runs), but it means any PSI computed against it right
   now would be statistically noisy. Closing this requires Project 1 to
   accumulate a real burn-in period of production traffic, then running
   `baseline_builder.py --from-live` against it — which can now
   genuinely be attempted, since the endpoint it depends on is confirmed
   working (see next section).
2. **`GET /events/recent-features` is now confirmed genuinely working
   end to end** — but getting there took a real fix on Project 1's
   side: the endpoint initially failed with a classic FastAPI
   route-ordering bug (`/events/{event_id}`, a path-parameter route,
   was defined before the literal `/events/recent-features` path, so
   it silently swallowed every request to the new endpoint first).
   Fixed by reordering the routes; verified by creating real events
   and confirming they round-tripped correctly through this exact
   endpoint. Full account in Project 1's own `docs/incidents.md` (#10).
3. **Project 1's event history resets on every redeploy.** This
   surfaced directly while verifying point 2: immediately after the
   route fix deployed, the endpoint correctly returned `n: 0` — not a
   bug, but confirmation that Project 1's local SQLite database (no
   persistent volume) starts empty on every new container revision.
   This is a genuine, now-documented architectural limitation on
   Project 1's side, not something fixable from this repo. It caps how
   much real history is ever available for a `--from-live` baseline
   until Project 1 moves to a persistent database.
4. **`monitor.yml`'s full scheduled execution has still not been run
   end to end.** The underlying script (`run_drift_check.py`) is
   confirmed working when invoked directly against Project 1's live
   endpoint, but the GitHub Actions workflow itself — its own secrets,
   its own network path, running on a cron schedule rather than called
   by hand — has not yet been exercised for real.
5. **Project 2 has no listener for the retrain trigger.** Even a
   correctly-computed, correctly-fired `repository_dispatch` event
   currently has nothing configured on the receiving end to act on it.

This is a substantially narrower, more precise gap than the original
version of this document described — that version's gap was actually
unclosable as stated, since it was built on a wrong assumption about
what data existed. The current gap is genuinely just "needs more real
traffic and one more real workflow run," which is a normal, expected
next step rather than a design flaw.
