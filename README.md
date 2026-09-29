# Sales Crediting Platform Prototype (with AI-Powered Root Cause Analysis)

A working prototype of a pharma Sales Crediting / Incentive Compensation
data pipeline -- built to demonstrate the exact stack a role like BMS's
"Sales Crediting Platform" position needs: SQL/Python data engineering,
business-rule translation, reconciliation frameworks, anomaly detection,
and a GenAI layer for root-cause analysis and stakeholder reporting.

## What this demonstrates (mapped to the JD)

| JD requirement | What's built |
|---|---|
| "Own day-to-day operations... ensuring accurate, timely and reliable processing of sales crediting" | `etl_pipeline.py` -- full ingest-to-credited-output pipeline |
| "Translate business requirements, sales crediting rules... into technical requirements" | `apply_credit_split()` -- turns territory credit-split rules (including shared/overlapping territories) into row-level logic |
| "Establish robust data quality, validation and reconciliation frameworks" | `validate_credit_rules()` + `reconcile()` -- catches broken rules and credited-vs-sales mismatches |
| "Monitor platform performance, identify data/process issues, perform root-cause analysis" | `anomaly_detection.py` -- rep payout spikes + source-system volume spikes |
| "Explore practical applications of AI for... anomaly detection, issue identification... operational insights" | `ai_layer.py` -- GenAI root-cause hypotheses + leadership-ready ops summary |
| "Communicate complex technical and data concepts clearly to non-technical stakeholders" | The AI layer's output is specifically written for an IC/Commercial Ops audience, not engineers |

## Design principle (your best interview talking point)

Same discipline as any production data platform: **every number is
computed and verified in Python before the LLM ever sees it.** The LLM's
job is strictly to hypothesize root causes and write stakeholder-facing
narrative -- never to calculate or invent a number. This is critical in
Incentive Compensation specifically, since crediting errors directly
affect rep pay -- you cannot let a model "guess" at a dollar figure.

## Architecture

```
generate_mock_data.py
  -> reps.csv, territories.csv, credit_rules.csv, raw_sales.csv
        |
        v
etl_pipeline.py
  1. ingest()               -- load raw + reference tables
  2. validate_credit_rules()-- data quality gate: do credit splits sum to 100%?
  3. apply_credit_split()   -- explode sales into per-rep credited rows
  4. reconcile()            -- credited total vs. original sales_amount, per txn
  5. rep_month_summary()    -- aggregated output that feeds an IC payout cycle
        |
        v
anomaly_detection.py
  - rep_payout_anomalies()      -- MoM payout spikes per rep
  - source_system_anomalies()   -- MoM transaction volume spikes per source feed
        |
        v
ai_layer.py  (chained prompts)
  Step 1: Root Cause Hypothesis   -- per broken rule / anomaly found
  Step 2: Operational Readiness Summary -- combines everything into one
          leadership-ready status update for an IC cycle kickoff
```

## Files

| File | Purpose |
|---|---|
| `generate_mock_data.py` | Creates a realistic mock dataset: 40 reps, 25 territories (some with shared/split credit rules), 4,000 raw sales transactions across 3 source systems -- with one intentionally broken credit rule injected for the demo |
| `etl_pipeline.py` | Core business logic: ingest, validate, apply credit-split rules, reconcile, summarize |
| `anomaly_detection.py` | Rep-level and source-system-level anomaly flags |
| `ai_layer.py` | The 2-step GenAI prompt chain (root cause + ops summary) |
| `main.py` | Runs everything end-to-end |

## How to run it

```bash
pip install pandas anthropic
python generate_mock_data.py
export ANTHROPIC_API_KEY="sk-..."   # optional -- see below
python main.py
```

No API key? `main.py` still runs the entire pipeline and anomaly
detection for real, and prints exactly what prompt would be sent to the
LLM at each step (dry-run mode) -- so you can demo/inspect the full
design without needing a key.

**Verified output from a test run:** the pipeline correctly caught an
intentionally broken credit rule (one territory's split summed to 80%,
not 100%), traced it to 169 affected transactions via the reconciliation
check, and flagged 48 rep-level and 3 source-system-level anomalies --
all from a single `python main.py` run.

## Porting to PySpark/Databricks

Built in pandas for portability, but every transformation maps directly
onto PySpark, since the JD specifically calls out Databricks:

| pandas (this repo) | PySpark/Databricks equivalent |
|---|---|
| `pd.read_csv(path)` | `spark.read.csv(path, header=True, inferSchema=True)` |
| `df.merge(other, on=col)` | `df.join(other, on=col)` |
| `df.groupby(col).sum()` | `df.groupBy(col).sum()` |
| `df.to_csv(path)` | `df.write.csv(path)` or write to a Delta table |

## How to talk about this project in an interview

> "I built a working prototype of a sales crediting pipeline that takes
> raw multi-source sales data, applies territory-based credit-split
> business rules -- including shared territories with partial-credit
> splits -- and produces a reconciled, rep-level credited output. I built
> in a validation gate that catches credit rules that don't sum to 100%
> before they'd silently mis-credit a rep, plus anomaly detection for
> payout spikes and source-system volume issues. On top of that, I added
> a GenAI layer that generates root-cause hypotheses and a leadership-
> ready operational readiness summary -- but critically, the model never
> calculates a number itself; it only narrates findings that the
> pipeline has already computed and verified. That distinction matters a
> lot in Incentive Compensation, where a wrong number directly affects
> someone's pay."
