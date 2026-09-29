"""
ai_layer.py
------------
GenAI layer covering the JD's "Technology, Automation & AI" section:
"Explore practical applications of AI for areas such as data validation,
anomaly detection, issue identification, process automation, documentation
and operational insights."

Same core design principle as before: Python computes and verifies every
number; the LLM only narrates and hypothesizes ROOT CAUSES in plain
English for non-technical Incentive Compensation stakeholders. The model
is explicitly told not to invent numbers -- only to reason over facts it's
given.

Two chained prompts:
  1. ROOT_CAUSE_PROMPT      -- given a reconciliation break or anomaly,
                                hypothesize likely causes a data engineer
                                would investigate first
  2. OPS_SUMMARY_PROMPT     -- combines all findings into a single
                                operational readiness summary for an
                                Incentive Compensation cycle kickoff
"""

import json
import os

ROOT_CAUSE_PROMPT = """You are a data engineer supporting a pharma Sales
Crediting Platform for Incentive Compensation. Below are FACTS about a
data quality issue, already calculated from the pipeline -- do not invent
or recalculate any numbers.

ISSUE FACTS (JSON):
{issue_facts}

Task: Write a short root-cause hypothesis (2-3 sentences) a data engineer
would investigate first. Consider common causes such as: a credit-split
rule that doesn't sum to 100%, a duplicate or late-arriving file from a
source system, or a territory realignment that wasn't reflected in the
rules table yet. Be specific to the facts given -- don't list generic
possibilities that don't fit the numbers shown."""


OPS_SUMMARY_PROMPT = """You are preparing an operational readiness summary
for an Incentive Compensation cycle kickoff meeting. Audience: IC
managers and Commercial Ops leadership -- non-technical, time-constrained.

PIPELINE FACTS (JSON):
{pipeline_facts}

ROOT CAUSE HYPOTHESES ALREADY GENERATED:
{root_causes}

Task: Write a single operational readiness paragraph (5-6 sentences) that:
- States whether the platform is ready to proceed with this cycle's
  crediting run, or needs issues resolved first
- Summarizes the data quality issues found, referencing the root causes
- Ends with a clear, specific recommended action and owner (e.g.,
  "IC Ops should confirm the TERR011 split correction before rerunning")

Tone: direct and operational, like a status update to leadership before
a compensation cycle -- no hedging, no generic filler."""


def call_llm(prompt, label):
    dry_run = os.environ.get("ANTHROPIC_API_KEY") is None
    if dry_run:
        print(f"\n{'=' * 70}\n[DRY RUN] Prompt -- {label}\n{'=' * 70}\n{prompt}")
        return f"[DRY RUN -- set ANTHROPIC_API_KEY for a real {label}]"
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def generate_root_cause(issue_facts: dict) -> str:
    prompt = ROOT_CAUSE_PROMPT.format(issue_facts=json.dumps(issue_facts, indent=2))
    return call_llm(prompt, "Root Cause Hypothesis")


def generate_ops_summary(pipeline_facts: dict, root_causes: list) -> str:
    prompt = OPS_SUMMARY_PROMPT.format(
        pipeline_facts=json.dumps(pipeline_facts, indent=2),
        root_causes="\n".join(f"- {rc}" for rc in root_causes),
    )
    return call_llm(prompt, "Operational Readiness Summary")
