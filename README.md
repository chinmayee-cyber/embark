# Financial Escalation Detection System

AI-powered pipeline that detects, classifies, and recommends actions for financial escalations across three domains: recurring costs, tax obligations, and payroll compliance.

---

## Architecture

```
data/                      ← synthetic dataset (3 JSON files, 39 records)
src/
  models/                  ← Pydantic schemas + constants/thresholds
  engines/
    watcher_engine.py      ← Rule engine: detects anomalies (no LLM)
    classifier_engine.py   ← Rule engine: assigns severity + owner (no LLM)
  agent/
    advisor_agent.py       ← AI agent: Agno + Gemini (LLM-powered)
    prompts.py             ← System and user prompt templates
  pipeline/
    loader.py              ← JSON → Pydantic model loader
    run_pipeline.py        ← Main orchestrator (entrypoint)
outputs/
  escalation_log.json      ← Generated on each run
```

---

## Setup

```bash
# 1. Clone and enter the project
cd financial-escalation-system

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

---

## Run

```bash
python src/pipeline/run_pipeline.py
```

Output is written to `outputs/escalation_log.json`.

---

## Key Design Decisions

**Only one AI agent (the Advisor).** The Watcher and Classifier are deterministic rule engines — calling them "agents" would be misleading. They have no LLM calls, no non-determinism, and no reasoning capability.

**No tools on the Gemini agent.** Gemini does not support `response_model` + tools simultaneously in Agno (raises a 400 INVALID_ARGUMENT). The Advisor enforces structured JSON output via system prompt instead.

**Cross-domain detection is rule-based, not LLM-based.** The engine identifies cross-domain links (same vendor or worker across domains) deterministically before the LLM call, and injects the context into the prompt. The LLM is given this context but the structural linkage is not left to it to discover.

---

## Adding a real data source (Phase 2)

Replace the `load_*` functions in `src/pipeline/loader.py` with your bank feed / ERP API calls. All downstream logic is data-source agnostic.
