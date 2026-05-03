# Scope of Work (SOW)
## AI-Powered Financial Escalation Detection System (PoC)

**Version:** 1.0  
**Date:** May 2026  
**Status:** Final (PoC-aligned)  
**Classification:** Confidential

## 1) Purpose and Background
This Scope of Work defines the implemented Phase 1 PoC for an AI-assisted financial escalation workflow focused on early detection of liabilities in three domains:
- Recurring costs
- Tax obligations
- Payroll compliance

The PoC replaces manual review with a deterministic detection/classification pipeline and an LLM-backed advisory layer for recommendations.

## 2) Project Scope
### 2.1 In Scope (Implemented)
- Synthetic dataset processing from local JSON files (`data/recurring_costs.json`, `data/tax_obligations.json`, `data/payroll_records.json`).
- Rule-based watcher engine to detect anomalies across:
  - Unused/unowned recurring subscriptions
  - Subscription review staleness
  - TDS/GST/PF/ESI due/overdue/penalty and ITC mismatch conditions
  - Payroll PF enrollment gaps, ESI threshold breaches, and F&F delays
- Rule-based classifier engine to assign:
  - Severity (`CRITICAL`, `MEDIUM`, `LOW`)
  - Owner (`Founder`, `Finance Lead`)
  - SLA hours (`0`, `48`, `72`)
- LLM advisor component (Agno + Gemini) to generate recommendations for escalations.
- Structured run output log generation at `outputs/escalation_log.json`.
- Executive HTML report generation at `outputs/escalation_report.html`.

### 2.2 Out of Scope (PoC)
- User-facing application UI beyond generated HTML report artifact.
- Database/persistent state management (pipeline is run-based).
- Live integrations (ERP/accounting/bank feeds/payroll systems).
- Multi-tenant architecture, authentication, and RBAC.
- Real-time streaming ingestion.
- Workflow automation for ticketing, notifications, or approvals.

## 3) Deliverables
| Ref | Deliverable | Description | Format |
|---|---|---|---|
| D1 | Synthetic Dataset | Three JSON files totaling 39 records | JSON |
| D2 | Rule Engines | Watcher + Classifier deterministic modules | Python |
| D3 | Advisor Agent | Agno + Gemini-based recommendation module | Python |
| D4 | Pipeline Orchestrator | End-to-end runner (`run_pipeline.py`) | Python |
| D5 | Output Log | Structured escalation and recommendation output | JSON |
| D6 | Executive Report | Styled leadership report generated from pipeline output | HTML |

## 4) Assumptions and Constraints
- Currency and compliance context are India-specific (INR, TDS/GST/PF/ESI logic used by rules).
- Input data is synthetic and file-based.
- LLM recommendations depend on configured Gemini API credentials (`GOOGLE_API_KEY` or `GEMINI_API_KEY`).
- No external datastore; each run is independent.
- Classification and anomaly detection are deterministic; advisory text can vary by model response.

## 5) Acceptance Criteria (PoC Completion)
- Pipeline successfully loads and processes all 39 synthetic records.
- Watcher emits anomaly events according to implemented rule conditions.
- Classifier assigns severity, owner, and SLA for all anomaly events.
- Pipeline writes a valid `outputs/escalation_log.json`.
- Pipeline writes a valid `outputs/escalation_report.html`.
- LLM advisory step executes when API key is present; if unavailable, pipeline still completes and logs warning state.

## 6) Exclusions and Change Control
Any requirement not listed in Section 2.1 is excluded from this PoC scope.  
Any expansion (live integrations, DB, UI app, real-time processing, enterprise controls) should be treated as a separate phase with revised timeline and effort.
