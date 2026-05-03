"""
Watcher Rule Engine
────────────────────
Deterministic rule-based engine. No LLM calls.
Ingests all three data streams, applies trigger conditions,
and emits structured AnomalyEvent objects.
"""

from datetime import date, timedelta
from typing import List

from src.models.schemas import RecurringCost, TaxObligation, PayrollRecord, AnomalyEvent
from src.models.constants import (
    SUBSCRIPTION_UNUSED_DAYS,
    SUBSCRIPTION_NOT_REVIEWED_DAYS,
    TDS_CRITICAL_DAYS_BEFORE_DUE,
    GST_MEDIUM_DAYS_BEFORE_DUE,
    ESI_THRESHOLD_INR,
    PF_ENROLLMENT_WINDOW_DAYS,
    FFS_DELAYED_MEDIUM_DAYS,
)


class WatcherEngine:
    """
    Scans all three data domains and emits anomaly events.
    Each public method returns a list of AnomalyEvent objects.
    run() aggregates all domains and returns the full event list.
    """

    def __init__(self, reference_date: date | None = None):
        self.today = reference_date or date.today()

    # ─── Recurring Costs ──────────────────────────────────────────────────────

    def scan_recurring_costs(self, records: List[RecurringCost]) -> List[AnomalyEvent]:
        events = []
        for r in records:
            days_since_review = (self.today - r.last_reviewed_date).days

            # Trigger 1: Unused subscription still auto-renewing with no owner
            if (
                r.usage_flag == "N"
                and r.auto_renew == "Y"
                and r.owner is None
            ):
                events.append(AnomalyEvent(
                    source_id=r.id,
                    domain="recurring_cost",
                    trigger_type="unused_unowned_subscription",
                    description=(
                        f"{r.vendor_name} ({r.category}) is unused, auto-renewing, "
                        f"and has no owner. Monthly cost: ₹{r.amount_inr:,.0f}."
                    ),
                    amount_inr=r.amount_inr,
                    vendor_id=r.vendor_name,
                    raw_data=r.model_dump(mode="json"),
                ))

            # Trigger 2: Active subscription not reviewed in > 90 days
            elif (
                r.usage_flag == "Y"
                and days_since_review > SUBSCRIPTION_NOT_REVIEWED_DAYS
                and r.auto_renew == "Y"
            ):
                events.append(AnomalyEvent(
                    source_id=r.id,
                    domain="recurring_cost",
                    trigger_type="subscription_not_reviewed",
                    description=(
                        f"{r.vendor_name} has not been reviewed in {days_since_review} days "
                        f"(threshold: {SUBSCRIPTION_NOT_REVIEWED_DAYS}). "
                        f"Monthly cost: ₹{r.amount_inr:,.0f}."
                    ),
                    amount_inr=r.amount_inr,
                    vendor_id=r.vendor_name,
                    raw_data=r.model_dump(mode="json"),
                ))

        return events

    # ─── Tax Obligations ──────────────────────────────────────────────────────

    def scan_tax_obligations(self, records: List[TaxObligation]) -> List[AnomalyEvent]:
        events = []
        for r in records:
            if r.filed_status == "filed":
                continue  # nothing to flag

            days_until_due = (r.due_date - self.today).days
            days_overdue = (self.today - r.due_date).days

            # Trigger: Penalty already triggered
            if r.penalty_triggered == "Y":
                events.append(AnomalyEvent(
                    source_id=r.id,
                    domain="tax",
                    trigger_type="penalty_triggered",
                    description=(
                        f"{r.obligation_type} ({r.sub_type}) for {r.responsible_party} "
                        f"has an active penalty. Overdue by {days_overdue} days. "
                        f"Amount: ₹{r.amount_due_inr:,.0f}."
                    ),
                    amount_inr=r.amount_due_inr,
                    raw_data=r.model_dump(mode="json"),
                ))
                continue  # penalty triggered already covers the overdue case

            # Trigger: TDS overdue or due within 3 days
            if r.obligation_type == "TDS" and r.filed_status == "pending":
                if days_until_due <= TDS_CRITICAL_DAYS_BEFORE_DUE:
                    events.append(AnomalyEvent(
                        source_id=r.id,
                        domain="tax",
                        trigger_type="tds_due_imminent" if days_until_due >= 0 else "tds_overdue",
                        description=(
                            f"TDS ({r.sub_type}) for {r.responsible_party} "
                            f"{'due in ' + str(days_until_due) + ' days' if days_until_due >= 0 else 'overdue by ' + str(days_overdue) + ' days'}. "
                            f"Amount: ₹{r.amount_due_inr:,.0f}."
                        ),
                        amount_inr=r.amount_due_inr,
                        raw_data=r.model_dump(mode="json"),
                    ))

            # Trigger: GST due within 5 days
            elif r.obligation_type == "GST" and r.filed_status == "pending":
                if days_until_due <= GST_MEDIUM_DAYS_BEFORE_DUE:
                    events.append(AnomalyEvent(
                        source_id=r.id,
                        domain="tax",
                        trigger_type="gst_due_imminent",
                        description=(
                            f"GST ({r.sub_type}) due in {days_until_due} days. "
                            f"Amount: ₹{r.amount_due_inr:,.0f}."
                        ),
                        amount_inr=r.amount_due_inr,
                        raw_data=r.model_dump(mode="json"),
                    ))

            # Trigger: ITC mismatch
            elif r.obligation_type == "GST" and r.filed_status == "mismatch":
                events.append(AnomalyEvent(
                    source_id=r.id,
                    domain="tax",
                    trigger_type="itc_mismatch",
                    description=(
                        f"GST ITC mismatch detected for {r.responsible_party}. "
                        f"ITC claim at risk: ₹{r.amount_due_inr:,.0f}."
                    ),
                    amount_inr=r.amount_due_inr,
                    raw_data=r.model_dump(mode="json"),
                ))

            # Trigger: PF/ESI overdue by even 1 day
            elif r.obligation_type in ("PF", "ESI") and r.filed_status == "pending":
                if days_until_due < 0:
                    events.append(AnomalyEvent(
                        source_id=r.id,
                        domain="tax",
                        trigger_type="pf_esi_overdue",
                        description=(
                            f"{r.obligation_type} ({r.sub_type}) overdue by {days_overdue} days. "
                            f"Damages accruing. Amount: ₹{r.amount_due_inr:,.0f}."
                        ),
                        amount_inr=r.amount_due_inr,
                        raw_data=r.model_dump(mode="json"),
                    ))
                elif days_until_due <= 5:
                    events.append(AnomalyEvent(
                        source_id=r.id,
                        domain="tax",
                        trigger_type="pf_esi_due_soon",
                        description=(
                            f"{r.obligation_type} ({r.sub_type}) due in {days_until_due} days. "
                            f"Amount: ₹{r.amount_due_inr:,.0f}."
                        ),
                        amount_inr=r.amount_due_inr,
                        raw_data=r.model_dump(mode="json"),
                    ))

        return events

    # ─── Payroll Records ──────────────────────────────────────────────────────

    def scan_payroll_records(self, records: List[PayrollRecord]) -> List[AnomalyEvent]:
        events = []
        for r in records:
            days_since_joining = (self.today - r.date_of_joining).days

            # Trigger 1: Employee PF not enrolled past 30-day window
            if (
                r.classification == "employee"
                and r.pf_enrolled == "N"
                and days_since_joining > PF_ENROLLMENT_WINDOW_DAYS
            ):
                events.append(AnomalyEvent(
                    source_id=r.id,
                    domain="payroll",
                    trigger_type="pf_enrollment_missed",
                    description=(
                        f"{r.name} (employee, joined {r.date_of_joining}) "
                        f"has not been enrolled in PF after {days_since_joining} days. "
                        f"30-day enrollment window missed."
                    ),
                    worker_id=r.worker_id,
                    raw_data=r.model_dump(mode="json"),
                ))

            # Trigger 2: Contractor above ESI threshold with ESI not applied
            if (
                r.classification == "contractor"
                and r.monthly_gross_inr > ESI_THRESHOLD_INR
                and r.esi_applicable == "Y"
            ):
                events.append(AnomalyEvent(
                    source_id=r.id,
                    domain="payroll",
                    trigger_type="esi_threshold_breach",
                    description=(
                        f"{r.name} (contractor) earns ₹{r.monthly_gross_inr:,.0f}/month, "
                        f"above ESI threshold of ₹{ESI_THRESHOLD_INR:,.0f}. "
                        f"ESI not being applied."
                    ),
                    amount_inr=r.monthly_gross_inr,
                    worker_id=r.worker_id,
                    raw_data=r.model_dump(mode="json"),
                ))

            # Trigger 3: F&F settlement delayed
            if r.ffs_status == "delayed":
                days_delayed = r.ffs_days_delayed or 0
                events.append(AnomalyEvent(
                    source_id=r.id,
                    domain="payroll",
                    trigger_type="ffs_delayed",
                    description=(
                        f"{r.name}'s full & final settlement is overdue by {days_delayed} days "
                        f"since last working date {r.ffs_last_working_date}."
                    ),
                    amount_inr=r.monthly_gross_inr,
                    worker_id=r.worker_id,
                    raw_data=r.model_dump(mode="json"),
                ))

            # Trigger 4: Employee ESI not set up (for eligible employees)
            if (
                r.classification == "employee"
                and r.esi_applicable == "Y"
                and r.pf_enrolled == "N"
                and days_since_joining > PF_ENROLLMENT_WINDOW_DAYS
            ):
                # ESI gap is already implied when PF is also missing — avoid double-event
                # Only emit separately if PF is fine but ESI is not configured
                pass

        return events

    # ─── Main entry point ─────────────────────────────────────────────────────

    def run(
        self,
        costs: List[RecurringCost],
        taxes: List[TaxObligation],
        payroll: List[PayrollRecord],
    ) -> List[AnomalyEvent]:
        events: List[AnomalyEvent] = []
        events.extend(self.scan_recurring_costs(costs))
        events.extend(self.scan_tax_obligations(taxes))
        events.extend(self.scan_payroll_records(payroll))
        return events
