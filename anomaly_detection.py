"""
anomaly_detection.py
----------------------
Root-cause-style anomaly detection on top of the credited sales output.
Covers the JD's "monitor platform performance, identify data/process
issues, perform root-cause analysis" requirement.

Two kinds of anomalies detected:
  1. Rep-level payout spikes -- a rep's month-over-month credited amount
     jumps unusually (could be legitimate, could be a broken credit rule
     or duplicate transaction feed -- needs investigation either way).
  2. Source-system spikes -- a source system (e.g., IQVIA_Claims) suddenly
     sends a much larger volume of transactions than usual, which often
     indicates an upstream feed issue (duplicate file load, late-arriving
     backdated data, etc.) rather than a real sales trend.
"""

import pandas as pd


def rep_payout_anomalies(rep_month_summary: pd.DataFrame, threshold=0.5) -> pd.DataFrame:
    """Flags rep-months where credited_amount moved >= threshold (50% default)
    vs. the prior month for that rep."""
    df = rep_month_summary.sort_values(["rep_id", "month"]).copy()
    df["prev_amount"] = df.groupby("rep_id")["credited_amount"].shift(1)
    df["pct_change"] = (df["credited_amount"] - df["prev_amount"]) / df["prev_amount"]
    anomalies = df[df["pct_change"].abs() >= threshold].dropna(subset=["pct_change"])
    return anomalies[["rep_id", "month", "prev_amount", "credited_amount", "pct_change"]]


def source_system_anomalies(sales: pd.DataFrame, threshold=0.4) -> pd.DataFrame:
    """Flags source-system/month combinations with an unusual transaction
    count spike vs. the prior month -- a common early signal of an upstream
    feed problem (duplicate loads, delayed files landing all at once)."""
    sales = sales.copy()
    sales["month"] = pd.to_datetime(sales["date"]).dt.to_period("M").astype(str)
    counts = sales.groupby(["source_system", "month"]).size().reset_index(name="txn_count")
    counts = counts.sort_values(["source_system", "month"])
    counts["prev_count"] = counts.groupby("source_system")["txn_count"].shift(1)
    counts["pct_change"] = (counts["txn_count"] - counts["prev_count"]) / counts["prev_count"]
    anomalies = counts[counts["pct_change"].abs() >= threshold].dropna(subset=["pct_change"])
    return anomalies


if __name__ == "__main__":
    from etl_pipeline import ingest, apply_credit_split, rep_month_summary as get_summary

    sales, rules, reps, territories = ingest()
    credited = apply_credit_split(sales, rules)
    summary = get_summary(credited)

    print("=== Rep Payout Anomalies (>=50% MoM change) ===")
    print(rep_payout_anomalies(summary).to_string(index=False))

    print("\n=== Source System Volume Anomalies (>=40% MoM change) ===")
    print(source_system_anomalies(sales).to_string(index=False))
