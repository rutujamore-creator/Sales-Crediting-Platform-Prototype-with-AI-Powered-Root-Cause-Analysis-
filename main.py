"""
main.py
--------
Runs the full Sales Crediting Platform prototype end-to-end:
  1. ETL pipeline (ingest -> validate -> apply credit-split rules -> load)
  2. Anomaly detection (rep payout spikes, source-system volume spikes)
  3. AI layer (root-cause hypotheses + operational readiness summary)

Run:
  python generate_mock_data.py   # once, to create the mock dataset
  python main.py

Works without an API key (DRY RUN mode) -- all pipeline logic and
anomaly detection are 100% real; only the LLM narrative step is stubbed.
"""

import json
import os

from etl_pipeline import ingest, validate_credit_rules, apply_credit_split, reconcile, rep_month_summary
from anomaly_detection import rep_payout_anomalies, source_system_anomalies
from ai_layer import generate_root_cause, generate_ops_summary


def main():
    dry_run = os.environ.get("ANTHROPIC_API_KEY") is None
    if dry_run:
        print("NOTE: ANTHROPIC_API_KEY not set -- running in DRY RUN mode.")
        print("All pipeline logic and anomaly detection are real; only the "
              "LLM narrative step is stubbed.\n")

    # ---- Stage 1: ETL Pipeline ----
    sales, rules, reps, territories = ingest()
    broken_rules = validate_credit_rules(rules)
    credited = apply_credit_split(sales, rules)
    recon_breaks = reconcile(credited, sales)
    summary = rep_month_summary(credited)

    print(f"Pipeline: {len(sales)} raw transactions -> {len(credited)} credited rows")
    print(f"Data quality gate: {len(broken_rules)} territory(ies) with broken credit rules")
    print(f"Reconciliation: {len(recon_breaks)} transactions with credited != sales_amount\n")

    # ---- Stage 2: Anomaly Detection ----
    rep_anomalies = rep_payout_anomalies(summary)
    source_anomalies = source_system_anomalies(sales)
    print(f"Anomaly detection: {len(rep_anomalies)} rep payout anomalies, "
          f"{len(source_anomalies)} source-system volume anomalies\n")

    # ---- Stage 3: AI layer -- root cause + ops summary ----
    root_causes = []
    if not broken_rules.empty:
        for _, row in broken_rules.iterrows():
            issue = {
                "issue_type": "broken_credit_rule",
                "territory_id": row["territory_id"],
                "total_credit_pct": row["total_pct"],
                "expected_pct": 100,
            }
            rc = generate_root_cause(issue)
            root_causes.append(rc)

    pipeline_facts = {
        "total_transactions": len(sales),
        "broken_credit_rules_count": len(broken_rules),
        "reconciliation_breaks_count": len(recon_breaks),
        "rep_payout_anomalies_count": len(rep_anomalies),
        "source_system_anomalies_count": len(source_anomalies),
    }
    ops_summary = generate_ops_summary(pipeline_facts, root_causes)

    print("\n" + "=" * 70)
    print("FINAL OUTPUT")
    print("=" * 70)
    print(f"\nPipeline facts:\n{json.dumps(pipeline_facts, indent=2)}")
    print(f"\n--- Root Cause Hypotheses ---")
    for rc in root_causes:
        print(f"- {rc}")
    print(f"\n--- Operational Readiness Summary ---\n{ops_summary}")


if __name__ == "__main__":
    main()
