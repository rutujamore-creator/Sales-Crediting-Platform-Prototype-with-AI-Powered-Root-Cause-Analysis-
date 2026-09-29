"""
generate_mock_data.py
----------------------
Creates a realistic mock pharma Sales Crediting / Incentive Compensation
dataset: raw sales transactions from multiple source systems, territory
alignments, reps, and credit-split business rules.

This mirrors what a Sales Crediting Platform ingests in real life:
- Sales data lands from multiple sources (specialty pharmacy, IQVIA-style
  claims data, direct orders) and needs to be reconciled and credited to
  the right sales reps according to territory alignment rules.
- Some territories are "shared" (e.g., a key account split between a
  primary and secondary rep) which is where crediting gets non-trivial
  and is a common source of real-world data quality issues.

Run: python generate_mock_data.py
Outputs: reps.csv, territories.csv, credit_rules.csv, raw_sales.csv
"""

import csv
import random
from datetime import date, timedelta

random.seed(7)

REGIONS = ["Northeast", "Southeast", "Midwest", "West"]
PRODUCTS = ["OncoPlex", "ImmunoGuard", "CardioFlex", "NeuroCare"]
SOURCE_SYSTEMS = ["SpecialtyPharmacy", "IQVIA_Claims", "DirectOrder"]

# ---- Reps ----
reps = []
for i in range(1, 41):
    reps.append({"rep_id": f"REP{i:03d}", "rep_name": f"Rep {i}",
                 "region": random.choice(REGIONS)})

# ---- Territories ----
territories = []
for i in range(1, 26):
    territories.append({"territory_id": f"TERR{i:03d}",
                         "region": random.choice(REGIONS)})

# ---- Credit rules: most territories map 1 rep = 100%; some are shared ----
credit_rules = []
for t in territories:
    primary_rep = random.choice(reps)
    if random.random() < 0.2:
        # shared territory: primary/secondary split
        secondary_rep = random.choice([r for r in reps if r["rep_id"] != primary_rep["rep_id"]])
        split = random.choice([70, 60, 50])
        credit_rules.append({"territory_id": t["territory_id"], "rep_id": primary_rep["rep_id"], "credit_pct": split})
        credit_rules.append({"territory_id": t["territory_id"], "rep_id": secondary_rep["rep_id"], "credit_pct": 100 - split})
    else:
        credit_rules.append({"territory_id": t["territory_id"], "rep_id": primary_rep["rep_id"], "credit_pct": 100})

# Intentionally inject a handful of BROKEN rules (splits that don't sum to 100)
# -- this is exactly the kind of data quality issue a reconciliation framework should catch.
broken_territory = random.choice(territories)["territory_id"]
for rule in credit_rules:
    if rule["territory_id"] == broken_territory:
        rule["credit_pct"] = round(rule["credit_pct"] * 0.8)  # now sums to <100%

# ---- Raw sales transactions ----
start_date = date(2026, 1, 1)
rows = []
txn_id = 5000
for i in range(4000):
    territory = random.choice(territories)
    product = random.choice(PRODUCTS)
    source = random.choice(SOURCE_SYSTEMS)
    units = random.randint(1, 50)
    unit_price = {"OncoPlex": 1200, "ImmunoGuard": 850, "CardioFlex": 400, "NeuroCare": 600}[product]
    amount = round(units * unit_price * random.uniform(0.9, 1.1), 2)

    # inject occasional duplicate-looking / spike transactions for anomaly detection
    if random.random() < 0.02:
        amount *= random.uniform(3, 5)

    txn_date = start_date + timedelta(days=random.randint(0, 250))
    rows.append({
        "transaction_id": f"TXN{txn_id}",
        "date": txn_date.isoformat(),
        "territory_id": territory["territory_id"],
        "product": product,
        "source_system": source,
        "units": units,
        "sales_amount": amount,
    })
    txn_id += 1

rows.sort(key=lambda r: r["date"])

with open("reps.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=reps[0].keys()); w.writeheader(); w.writerows(reps)

with open("territories.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=territories[0].keys()); w.writeheader(); w.writerows(territories)

with open("credit_rules.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=credit_rules[0].keys()); w.writeheader(); w.writerows(credit_rules)

with open("raw_sales.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

print(f"Generated {len(reps)} reps, {len(territories)} territories, "
      f"{len(credit_rules)} credit rules, {len(rows)} raw sales transactions.")
print(f"NOTE: territory {broken_territory} has an intentionally broken credit "
      f"split (<100%) to demo the reconciliation framework catching it.")
