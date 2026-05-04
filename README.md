# Financial Escalation Detection System

## What is this project about?
This project is an AI-powered pipeline for detecting and recommending actions on financial escalations in Indian startups. It processes data across three domains—recurring costs, tax obligations, and payroll compliance—to identify anomalies, classify them by severity, and generate structured recommendations. The goal is to automate early detection of financial risks, reducing manual review and potential cost leakage.

## How does it do what it does?
The system uses a modular pipeline:
- **Data Loading**: Loads and validates financial records from JSON files using Pydantic models.
- **Anomaly Detection**: Rule-based engines scan for issues like unused subscriptions, overdue taxes, or compliance gaps.
- **Classification**: Assigns severity (Critical, Medium, Low), owner, and SLA to each anomaly.
- **AI Recommendations**: An LLM advisor (using Agno and Gemini) generates tailored actions for high-priority escalations.
- **Outputs**: Produces a JSON log and an HTML executive report for review.

The pipeline is deterministic for detection and classification, with AI only used for recommendations.

## How do we set it up and use it?
### Setup
1. Clone the repository and navigate to the project directory.
2. Create a virtual environment: `python -m venv .venv` (activate with `.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on macOS/Linux).
3. Install dependencies: `pip install -e ".[dev]"`.
4. Set up environment variables: Create `.env` and add your `GOOGLE_API_KEY` or `GEMINI_API_KEY` for AI recommendations.

### Usage
Run the pipeline with: `python src/pipeline/run_pipeline.py`.  
Outputs are saved to `outputs/escalation_log.json` (JSON data) and `outputs/escalation_report.html` (HTML report).  
If no API key is provided, the pipeline skips AI recommendations but still generates outputs.
