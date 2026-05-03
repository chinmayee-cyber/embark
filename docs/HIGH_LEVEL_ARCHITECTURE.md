# High-Level Architecture

```
Synthetic Data Inputs
(data/recurring_costs.json, data/tax_obligations.json, data/payroll_records.json)
    |
    v
Pipeline Orchestrator
(src/pipeline/run_pipeline.py)
    |
    v
Data Loader
(src/pipeline/loader.py - Pydantic model validation)
    |
    v
Watcher Engine
(src/engines/watcher_engine.py - Rule-based anomaly detection)
    |
    v
Classifier Engine
(src/engines/classifier_engine.py - Severity, owner, SLA assignment)
    |     \
    |      \
    v       v
Advisor Agent     Pipeline Output Model
(src/agent/advisor_agent.py - Agno + Gemini recommendations)   (src/models/schemas.py - PipelineOutput)
    |       ^
    v       |
Gemini API  |
(via Agno model adapter)     |
    |       |
    |       v
    |   JSON Output
    |   (outputs/escalation_log.json)
    |
    v
HTML Executive Report
(outputs/escalation_report.html)
```

