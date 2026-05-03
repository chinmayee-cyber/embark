"""
Classifier Rule Engine
───────────────────────
Deterministic rule-based engine. No LLM calls.
Takes AnomalyEvent objects from the Watcher and produces
EscalationEvent objects with severity, owner, and SLA assigned.
"""

from datetime import date, timedelta
from typing import List

from src.models.schemas import AnomalyEvent, EscalationEvent
from src.models.constants import Severity, Owner, SLA_HOURS, HIGH_VALUE_SUBSCRIPTION_INR


# ─── Severity and Owner classification rules ──────────────────────────────────
# Each rule is a tuple: (trigger_type_match, severity, owner)
# Evaluated in order — first match wins.

CLASSIFICATION_RULES: list[tuple[str, Severity, Owner]] = [
    # CRITICAL rules
    ("penalty_triggered",           Severity.CRITICAL, Owner.FOUNDER),
    ("tds_overdue",                 Severity.CRITICAL, Owner.FOUNDER),
    ("pf_esi_overdue",              Severity.CRITICAL, Owner.FOUNDER),
    ("pf_enrollment_missed",        Severity.CRITICAL, Owner.FINANCE_LEAD),
    ("ffs_delayed",                 Severity.CRITICAL, Owner.FINANCE_LEAD),

    # MEDIUM rules
    ("tds_due_imminent",            Severity.MEDIUM,   Owner.FINANCE_LEAD),
    ("gst_due_imminent",            Severity.MEDIUM,   Owner.FINANCE_LEAD),
    ("itc_mismatch",                Severity.MEDIUM,   Owner.FINANCE_LEAD),
    ("pf_esi_due_soon",             Severity.MEDIUM,   Owner.FINANCE_LEAD),
    ("esi_threshold_breach",        Severity.MEDIUM,   Owner.FINANCE_LEAD),

    # LOW rules (catch-all for cost hygiene)
    ("unused_unowned_subscription", Severity.LOW,      Owner.FINANCE_LEAD),
    ("subscription_not_reviewed",   Severity.LOW,      Owner.FINANCE_LEAD),
]


def _upgrade_unused_subscription(event: AnomalyEvent) -> Severity:
    """
    Unused subscriptions with monthly cost above the high-value threshold
    are upgraded from LOW to MEDIUM.
    """
    if (
        event.trigger_type == "unused_unowned_subscription"
        and event.amount_inr is not None
        and event.amount_inr > HIGH_VALUE_SUBSCRIPTION_INR
    ):
        return Severity.MEDIUM
    return Severity.LOW


class ClassifierEngine:
    """
    Applies severity rules to each AnomalyEvent and returns
    a list of EscalationEvent objects ready for the advisor.
    """

    def __init__(self, reference_date: date | None = None):
        self.today = reference_date or date.today()

    def _classify(self, event: AnomalyEvent) -> tuple[Severity, Owner]:
        for trigger, severity, owner in CLASSIFICATION_RULES:
            if event.trigger_type == trigger:
                # Apply value-based upgrade for subscriptions
                if trigger == "unused_unowned_subscription":
                    severity = _upgrade_unused_subscription(event)
                return severity, owner
        # Default fallback — should not be hit with a complete rule set
        return Severity.LOW, Owner.FINANCE_LEAD

    def _deadline(self, severity: Severity) -> str:
        hours = SLA_HOURS[severity]
        if hours == 0:
            return self.today.isoformat()
        deadline = self.today + timedelta(hours=hours)
        return deadline.isoformat()

    def classify(self, events: List[AnomalyEvent]) -> List[EscalationEvent]:
        escalations: List[EscalationEvent] = []
        for event in events:
            severity, owner = self._classify(event)
            escalations.append(EscalationEvent(
                source_id=event.source_id,
                domain=event.domain,
                trigger_type=event.trigger_type,
                description=event.description,
                severity=severity,
                owner=owner,
                sla_hours=SLA_HOURS[severity],
                amount_inr=event.amount_inr,
                vendor_id=event.vendor_id,
                worker_id=event.worker_id,
                raw_data=event.raw_data,
            ))

        # Sort: CRITICAL first, then MEDIUM, then LOW
        order = {Severity.CRITICAL: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
        escalations.sort(key=lambda e: order[e.severity])
        return escalations

    def run(self, events: List[AnomalyEvent]) -> List[EscalationEvent]:
        return self.classify(events)
