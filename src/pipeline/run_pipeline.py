"""
Pipeline Orchestrator
──────────────────────
Single entrypoint. Runs the full pipeline:
  1. Load data (3 JSON files)
  2. Watcher rule engine → anomaly events
  3. Classifier rule engine → escalation events (severity + owner)
  4. Advisor AI agent (Agno + Gemini) → recommendations
  5. Write structured output log to outputs/escalation_log.json
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# ── ensure project root is on sys.path when run directly ──────────────────────
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline.loader import load_recurring_costs, load_tax_obligations, load_payroll_records
from src.engines.watcher_engine import WatcherEngine
from src.engines.classifier_engine import ClassifierEngine
from src.agent.advisor_agent import AdvisorAgent
from src.models.schemas import PipelineOutput
from src.models.constants import Severity
from src.pipeline.report_generator import generate_html_report

load_dotenv()


def run_pipeline(
    model_id: str = "gemini-2.0-flash",
    reference_date: date | None = None,
    output_path: Path | None = None,
) -> PipelineOutput:
    today = reference_date or date.today()
    errors: list[str] = []

    # ── Step 1: Load data ─────────────────────────────────────────────────────
    print("\n[1/4] Loading synthetic dataset...")
    try:
        costs = load_recurring_costs()
        taxes = load_tax_obligations()
        payroll = load_payroll_records()
        total_records = len(costs) + len(taxes) + len(payroll)
        print(f"      Loaded {len(costs)} recurring costs, {len(taxes)} tax obligations, "
              f"{len(payroll)} payroll records  ({total_records} total)")
    except Exception as e:
        raise RuntimeError(f"Failed to load data: {e}") from e

    # ── Step 2: Watcher rule engine ───────────────────────────────────────────
    print("\n[2/4] Running watcher rule engine...")
    watcher = WatcherEngine(reference_date=today)
    anomalies = watcher.run(costs, taxes, payroll)
    print(f"      Detected {len(anomalies)} anomalies")
    for a in anomalies:
        print(f"      · [{a.domain:15s}] {a.source_id:8s} — {a.trigger_type}")

    # ── Step 3: Classifier rule engine ────────────────────────────────────────
    print("\n[3/4] Running classifier rule engine...")
    classifier = ClassifierEngine(reference_date=today)
    escalations = classifier.run(anomalies)

    severity_counts = {s.value: 0 for s in Severity}
    for e in escalations:
        severity_counts[e.severity.value] += 1

    print(f"      Classified {len(escalations)} escalations:")
    print(f"      · CRITICAL : {severity_counts['CRITICAL']}")
    print(f"      · MEDIUM   : {severity_counts['MEDIUM']}")
    print(f"      · LOW      : {severity_counts['LOW']}")

    # ── Step 4: Advisor AI agent ──────────────────────────────────────────────
    gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        errors.append("GOOGLE_API_KEY / GEMINI_API_KEY not set — advisor agent will fail.")
        print("\n[4/4] WARNING: No Gemini API key found. Skipping advisor agent.")
        recommendations = []
        api_calls = 0
    else:
        print(f"\n[4/4] Running advisor AI agent (Agno + {model_id})...")
        advisor = AdvisorAgent(model_id=model_id, reference_date=today)
        recommendations = advisor.run(escalations)
        api_calls = advisor.api_calls_made

        api_errors = [r for r in recommendations if r.api_error]
        cross_domain = [r for r in recommendations if r.cross_domain_flag]
        print(f"      Generated {len(recommendations)} recommendations")
        print(f"      · LLM calls made   : {api_calls}")
        print(f"      · API errors       : {len(api_errors)}")
        print(f"      · Cross-domain     : {len(cross_domain)}")

        if api_errors:
            for r in api_errors:
                errors.append(f"API error on {r.source_id}: {r.reasoning}")

    # ── Assemble output ───────────────────────────────────────────────────────
    output = PipelineOutput(
        run_date=today.isoformat(),
        records_processed=total_records,
        anomalies_detected=len(anomalies),
        escalations_by_severity=severity_counts,
        api_calls_made=api_calls if gemini_key else 0,
        errors=errors,
        escalations=escalations,
        recommendations=recommendations,
    )

    # ── Write output log ──────────────────────────────────────────────────────
    out_path = output_path or ROOT / "outputs" / "escalation_log.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Generate executive HTML report ────────────────────────────────────────
    report_path = out_path.parent / "escalation_report.html"
    generate_html_report(output, report_path)

    print(f"\n[OK] Pipeline complete. Output written to: {out_path}")
    print(f"  Report (HTML)     : {report_path}")
    print(f"  Records processed : {output.records_processed}")
    print(f"  Anomalies found   : {output.anomalies_detected}")
    print(f"  Escalations       : {len(escalations)}")
    print(f"  Recommendations   : {len(recommendations)}")
    if errors:
        print(f"  Errors            : {len(errors)}")
        for err in errors:
            print(f"  [WARN] {err}")

    return output


if __name__ == "__main__":
    run_pipeline()
