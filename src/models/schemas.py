from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field
from src.models.constants import Severity, ObligationType, Owner, WorkerClassification, FiledStatus


# ─── Raw data models (loaded from JSON) ───────────────────────────────────────

class RecurringCost(BaseModel):
    id: str
    vendor_name: str
    category: str
    amount_inr: float
    frequency: str
    last_reviewed_date: date
    usage_flag: str           # "Y" or "N"
    auto_renew: str           # "Y" or "N"
    owner: Optional[str] = None
    notes: Optional[str] = None


class TaxObligation(BaseModel):
    id: str
    obligation_type: str
    sub_type: str
    due_date: date
    filed_status: str         # "pending", "filed", "mismatch"
    amount_due_inr: float
    penalty_triggered: str    # "Y" or "N"
    responsible_party: str
    notes: Optional[str] = None


class PayrollRecord(BaseModel):
    id: str
    worker_id: str
    name: str
    classification: str       # "employee" or "contractor"
    monthly_gross_inr: float
    date_of_joining: date
    pf_enrolled: str          # "Y", "N", or "N/A"
    esi_applicable: str       # "Y" or "N"
    last_payment_date: date
    ffs_status: str           # "N/A", "delayed"
    ffs_last_working_date: Optional[date] = None
    ffs_due_date: Optional[date] = None
    ffs_days_delayed: Optional[int] = None
    notes: Optional[str] = None


# ─── Pipeline intermediary models ─────────────────────────────────────────────

class AnomalyEvent(BaseModel):
    source_id: str            # e.g. "RC-003", "TAX-002"
    domain: str               # "recurring_cost", "tax", "payroll"
    trigger_type: str         # human-readable trigger label
    description: str
    amount_inr: Optional[float] = None
    vendor_id: Optional[str] = None    # for cross-domain linking
    worker_id: Optional[str] = None    # for cross-domain linking
    raw_data: dict = Field(default_factory=dict)


class EscalationEvent(BaseModel):
    source_id: str
    domain: str
    trigger_type: str
    description: str
    severity: Severity
    owner: Owner
    sla_hours: int
    amount_inr: Optional[float] = None
    vendor_id: Optional[str] = None
    worker_id: Optional[str] = None
    raw_data: dict = Field(default_factory=dict)


# ─── Advisor agent output model ───────────────────────────────────────────────

class Recommendation(BaseModel):
    source_id: str
    action: str
    financial_exposure_inr: float
    owner: str
    deadline: str             # ISO date string
    cross_domain_flag: bool = False
    linked_records: list[str] = Field(default_factory=list)
    reasoning: str
    api_error: bool = False


# ─── Final pipeline output ────────────────────────────────────────────────────

class PipelineOutput(BaseModel):
    run_date: str
    records_processed: int
    anomalies_detected: int
    escalations_by_severity: dict[str, int]
    api_calls_made: int
    errors: list[str]
    escalations: list[EscalationEvent]
    recommendations: list[Recommendation]
