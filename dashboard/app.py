"""
dashboard/app.py

Observability dashboard for the log-anomaly classifier deployed in
Project 1 (Log Anomaly Detection Platform). Pulls live request
telemetry from the same Application Insights workspace Project 1
already emits data to, computes drift against a stored baseline, and
surfaces the metrics that actually apply to a classifier — NOT
generative-LLM-specific metrics like hallucination rate or token cost,
which don't apply to this model type (see README's honest scoping note).

Install once:
  pip install streamlit azure-monitor-query azure-identity pandas plotly

Usage:
  streamlit run app.py
"""

import json
import sys
import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "drift"))
from psi import compute_psi, interpret_psi, compute_feature_drift_report

st.set_page_config(page_title="Log Anomaly Model — Observability", layout="wide")

WORKSPACE_ID = os.environ.get("LOG_ANALYTICS_WORKSPACE_ID", "")
BASELINE_PATH = os.environ.get("BASELINE_PATH", "../drift/baseline.json")
LOG_ANOMALY_API_URL = os.environ.get("LOG_ANOMALY_API_URL", "")
LOG_ANOMALY_API_TOKEN = os.environ.get("LOG_ANOMALY_API_TOKEN", "")
DRIFT_THRESHOLD = 0.25


@st.cache_data(ttl=300)
def load_baseline() -> dict:
    with open(BASELINE_PATH) as f:
        return json.load(f)


@st.cache_data(ttl=60)
def query_recent_requests(workspace_id: str, hours: int = 24) -> pd.DataFrame:
    """Pulls recent request telemetry from the same App Insights
    workspace Project 1 already emits to. Returns an empty DataFrame
    (handled gracefully by the UI) if the query fails or no workspace
    is configured — this dashboard should degrade to a clear "no data"
    state, not crash, if run without live Azure access."""
    if not workspace_id:
        return pd.DataFrame()

    try:
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)
        query = f"""
        requests
        | where timestamp > ago({hours}h)
        | project timestamp, name, duration, success, resultCode
        | order by timestamp asc
        """
        response = client.query_workspace(workspace_id=workspace_id, query=query, timespan=None)
        if response.status != LogsQueryStatus.SUCCESS or not response.tables[0].rows:
            return pd.DataFrame()

        table = response.tables[0]
        return pd.DataFrame(table.rows, columns=[c for c in table.columns])
    except Exception as e:
        st.warning(f"Could not query live telemetry ({type(e).__name__}). "
                   f"Showing baseline-only view.")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def query_current_features(api_url: str, token: str) -> dict | None:
    """Pulls real, current feature data from Project 1's
    /events/recent-features endpoint. Returns None (handled gracefully
    by the UI) if no API URL/token is configured or the request fails —
    this dashboard should say plainly that live comparison data isn't
    available, not silently fall back to fabricated numbers."""
    if not api_url or not token:
        return None
    try:
        response = requests.get(
            f"{api_url}/events/recent-features",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if data["n"] < 20:
            return None  # too few real events yet to be a meaningful comparison
        return {"confidence": data["confidence"], "text_length": data["text_length"]}
    except Exception:
        return None


def render_drift_section(baseline: dict, current_features: dict | None):
    st.subheader("Feature Drift (Population Stability Index)")

    if current_features is None:
        st.info("No live feature data available yet — drift comparison requires "
                "logging actual input features per request (see README's "
                "'what I'd add next' for wiring this up against Project 1's DB).")
        return

    report = compute_feature_drift_report(baseline, current_features, list(baseline.keys()))

    cols = st.columns(len(report))
    for col, (feature_name, result) in zip(cols, report.items()):
        with col:
            color = "🟢" if result["psi"] < 0.10 else ("🟡" if result["psi"] < 0.25 else "🔴")
            st.metric(label=feature_name, value=f"{result['psi']:.3f}")
            st.caption(f"{color} {result['interpretation']}")

    max_psi = max(r["psi"] for r in report.values())
    if max_psi > DRIFT_THRESHOLD:
        st.error(f"⚠️ Drift threshold ({DRIFT_THRESHOLD}) exceeded — "
                 f"retraining trigger would fire here in the scheduled workflow.")


def render_traffic_section(df: pd.DataFrame):
    st.subheader("Request Volume & Latency")

    if df.empty:
        st.info("No live telemetry available. Showing this section requires "
                "LOG_ANALYTICS_WORKSPACE_ID set and network access to Azure Monitor.")
        return

    col1, col2 = st.columns(2)
    with col1:
        volume_by_hour = df.set_index("timestamp").resample("1H").size()
        fig = px.line(volume_by_hour, title="Requests per hour")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.histogram(df, x="duration", title="Latency distribution (ms)", nbins=30)
        st.plotly_chart(fig, use_container_width=True)

    success_rate = (df["success"] == True).mean() * 100 if "success" in df else None
    if success_rate is not None:
        st.metric("Success rate", f"{success_rate:.1f}%")


def main():
    st.title("🚨 Log Anomaly Model — Observability Dashboard")
    st.caption(
        "Monitoring for `oromeop/log-classifier-tiny` as deployed in "
        "[Log Anomaly Detection Platform](https://github.com/sugarhillconsultants/log-anomaly-platform). "
        "Note: this model is a classifier, not a generative LLM — metrics here "
        "are feature/prediction drift, volume, and latency, not token cost or "
        "hallucination rate, which don't apply to this model type."
    )

    baseline = load_baseline()
    df = query_recent_requests(WORKSPACE_ID)
    current_features = query_current_features(LOG_ANOMALY_API_URL, LOG_ANOMALY_API_TOKEN)

    render_traffic_section(df)
    st.divider()
    render_drift_section(baseline, current_features)


if __name__ == "__main__":
    main()
