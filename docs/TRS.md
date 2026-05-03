# Technical Requirements Specification (TRS)
## AI-Powered Financial Escalation Detection System (PoC)

**Version:** 1.0  
**Date:** May 2026  
**Status:** Final (Codebase-aligned)

## 1) System Overview
The system is a Python 3.11+ pipeline that:
1. Loads synthetic financial records from JSON files.
2. Detects anomalies using deterministic rule engines.
3. Classifies anomalies into escalations with severity/owner/SLA.
4. Generates recommendations via an LLM advisor (Agno + Gemini).
5. Produces machine-readable JSON and an executive HTML report.

No database, web service, or live system integration is required in this PoC.

## 2) Data Requirements
### 2.1 Input Sources
- `data/recurring_costs.json` (15 records)
- `data/tax_obligations.json` (12 records)
- `data/payroll_records.json` (12 records)

### 2.2 Input Validation
Data is validated through Pydantic models in `src/models/schemas.py`:
- `RecurringCost`
- `TaxObligation`
- `PayrollRecord`

## 3) Functional Requirements
### 3.1 Watcher Engine (`src/engines/watcher_engine.py`)
Deterministic anomaly detection (no LLM calls).

Implemented triggers include:
- **Recurring costs**
  - `unused_unowned_subscription`
  - `subscription_not_reviewed`
- **Tax**
  - `penalty_triggered`
  - `tds_due_imminent`
  - `tds_overdue`
  - `gst_due_imminent`
  - `itc_mismatch`
  - `pf_esi_overdue`
  - `pf_esi_due_soon`
- **Payroll**
  - `pf_enrollment_missed`
  - `esi_threshold_breach`
  - `ffs_delayed`

### 3.2 Classifier Engine (`src/engines/classifier_engine.py`)
Deterministic mapping from trigger type to:
- `Severity`: `CRITICAL` / `MEDIUM` / `LOW`
- `Owner`: `Founder` / `Finance Lead`
- `SLA_HOURS`: `0`, `48`, `72`

Special implemented rule:
- `unused_unowned_subscription` is upgraded from `LOW` to `MEDIUM` when amount exceeds `HIGH_VALUE_SUBSCRIPTION_INR` (5000).

### 3.3 Advisor Agent (`src/agent/advisor_agent.py`)
LLM-backed recommendation generation.

Implementation characteristics:
- Framework: Agno (`agno.agent.Agent`)
- Model backend: Gemini (`agno.models.google.Gemini`)
- Default model id: `gemini-2.0-flash`
- Structured response enforced via prompt contract (JSON parsing handled manually)
- For `LOW` severity, templated recommendation path exists in code (no LLM call)
- Includes rule-based cross-domain linking index using `vendor_id` and `worker_id`
- API failure/parse failure returns fallback recommendation object with `api_error=true`

### 3.4 Pipeline Orchestration (`src/pipeline/run_pipeline.py`)
Execution sequence:
1. Load data
2. Run watcher
3. Run classifier
4. Run advisor (if API key available)
5. Build `PipelineOutput`
6. Write JSON log
7. Generate HTML report

Environment requirement for advisor execution:
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`

## 4) Output Requirements
### 4.1 JSON Output
Path: `outputs/escalation_log.json`  
Schema anchor: `PipelineOutput` model with fields:
- `run_date`
- `records_processed`
- `anomalies_detected`
- `escalations_by_severity`
- `api_calls_made`
- `errors`
- `escalations`
- `recommendations`

### 4.2 HTML Output
Path: `outputs/escalation_report.html`  
Generated via Jinja2 template rendering from pipeline output.

## 5) Non-Functional Requirements (PoC)
- **Determinism:** Watcher and classifier must produce identical outputs for identical inputs.
- **Modularity:** Independent importable modules by responsibility (`models`, `engines`, `agent`, `pipeline`).
- **Resilience:** Advisor failures should not crash the run; fallback handling/logging path is implemented.
- **Portability:** Single-command local execution via Python script.

## 6) Technology Stack
- **Language:** Python >= 3.11
- **Core libs:** `pydantic`, `python-dotenv`, `jinja2`
- **LLM stack:** `agno`, `google-generativeai` via Gemini model integration in Agno
- **Packaging:** `pyproject.toml` (setuptools backend)
- **Testing tooling configured:** `pytest` (dev dependency)

## 7) Known PoC Boundaries
- No persistent storage layer.
- No public API layer.
- No UI application (HTML report output only).
- No external data ingestion adapters.
- No production workflow automation (alerts, queues, ticketing) included.
