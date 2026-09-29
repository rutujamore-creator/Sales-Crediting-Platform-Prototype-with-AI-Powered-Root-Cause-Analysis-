"""
etl_pipeline.py
-----------------
The core Sales Crediting Platform logic: ingests raw sales transactions
from multiple source systems and applies territory-based credit-split
business rules to produce a credited-sales output table.

Written in pandas for portability/demo purposes, but the transformations
map 1:1 onto PySpark/Databricks (see README "Porting to PySpark" section)
-- every operation here (read_csv, merge, groupby, filter) has a direct
PySpark equivalent (spark.read.csv, join, groupBy, filter).

PIPELINE STAGES (mirrors a real ETL/ELT job):
  1. INGEST   -- load raw sales + reference tables (reps, territories, rules)
  2. VALIDATE -- check credit rules sum to 100% per territory (data quality gate)
  3. TRANSFORM-- explode each sale into per-rep credited rows using the
                 credit-split rules ("who gets credit for this sale, and
                 how much")
  4. LOAD     -- write the credited-sales output table
"""

import pandas as pd


def ingest(sales_path="raw_sales.csv", rules_path="credit_rules.csv",
           reps_path="reps.csv", territories_path="territories.csv"):
    sales = pd.read_csv(sales_path, parse_dates=["date"])
    rules = pd.read_csv(rules_path)
    reps = pd.read_csv(reps_path)
    territories = pd.read_csv(territories_path)
    return sales, rules, reps, territories


def validate_credit_rules(rules: pd.DataFrame) -> pd.DataFrame:
    """
    Data quality gate: every territory's credit_pct values must sum to 100.
    Returns a DataFrame of BROKEN territories (this is exactly the kind of
    issue a real Sales Crediting Platform must catch before it silently
    over/under-credits reps -- a direct P&L / compensation accuracy risk).
    """
    totals = rules.groupby("territory_id")["credit_pct"].sum().reset_index()
    totals.columns = ["territory_id", "total_pct"]
    broken = totals[totals["total_pct"] != 100].copy()
    return broken


def apply_credit_split(sales: pd.DataFrame, rules: pd.DataFrame) -> pd.DataFrame:
    """
    Explodes each sales transaction into one row per rep entitled to credit
    for that territory, per the credit-split rules. This is the central
    business-rule translation the JD describes: "translate sales crediting
    rules into technical requirements and implement scalable solutions."
    """
    merged = sales.merge(rules, on="territory_id", how="left")
    merged["credited_amount"] = merged["sales_amount"] * (merged["credit_pct"] / 100.0)
    merged["month"] = merged["date"].dt.to_period("M").astype(str)
    return merged


def reconcile(credited: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    """
    Reconciliation check: for each transaction, total credited_amount across
    all reps should equal the original sales_amount (i.e., 100% of every
    sale gets credited to someone, no more, no less). Any transaction that
    fails this check indicates a broken credit rule and needs escalation
    -- this is the "data quality, validation and reconciliation framework"
    the JD calls for directly.
    """
    txn_totals = credited.groupby("transaction_id")["credited_amount"].sum().reset_index()
    txn_totals.columns = ["transaction_id", "total_credited"]
    check = sales[["transaction_id", "sales_amount"]].merge(txn_totals, on="transaction_id")
    check["variance"] = (check["total_credited"] - check["sales_amount"]).round(2)
    breaks = check[check["variance"].abs() > 0.01]
    return breaks


def rep_month_summary(credited: pd.DataFrame) -> pd.DataFrame:
    """Aggregated output: credited sales by rep by month -- what an Incentive
    Compensation cycle actually consumes to calculate payouts."""
    summary = credited.groupby(["rep_id", "month"])["credited_amount"].sum().reset_index()
    return summary.sort_values(["rep_id", "month"])


def run_pipeline():
    sales, rules, reps, territories = ingest()

    broken_rules = validate_credit_rules(rules)
    credited = apply_credit_split(sales, rules)
    reconciliation_breaks = reconcile(credited, sales)
    summary = rep_month_summary(credited)

    credited.to_csv("credited_sales_output.csv", index=False)
    summary.to_csv("rep_month_summary.csv", index=False)

    return {
        "broken_credit_rules": broken_rules,
        "reconciliation_breaks": reconciliation_breaks,
        "rep_month_summary": summary,
        "total_transactions": len(sales),
        "total_credited_rows": len(credited),
    }


if __name__ == "__main__":
    results = run_pipeline()
    print(f"Ingested {results['total_transactions']} raw transactions "
          f"-> {results['total_credited_rows']} credited rows\n")

    print("=== Data Quality Gate: Broken Credit Rules (don't sum to 100%) ===")
    print(results["broken_credit_rules"].to_string(index=False) or "None found")

    print(f"\n=== Reconciliation Breaks: {len(results['reconciliation_breaks'])} "
          f"transactions where credited != sales_amount ===")
    print(results["reconciliation_breaks"].head(10).to_string(index=False))

    print("\n=== Sample Rep-Month Summary (feeds Incentive Compensation) ===")
    print(results["rep_month_summary"].head(10).to_string(index=False))
