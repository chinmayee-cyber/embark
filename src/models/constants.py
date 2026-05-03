from enum import Enum


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ObligationType(str, Enum):
    TDS = "TDS"
    GST = "GST"
    PF = "PF"
    ESI = "ESI"
    ADVANCE_TAX = "Advance Tax"


class Owner(str, Enum):
    FOUNDER = "Founder"
    FINANCE_LEAD = "Finance Lead"
    LEGAL = "Legal"


class WorkerClassification(str, Enum):
    EMPLOYEE = "employee"
    CONTRACTOR = "contractor"


class FiledStatus(str, Enum):
    PENDING = "pending"
    FILED = "filed"
    MISMATCH = "mismatch"


# ─── Business rule thresholds ─────────────────────────────────────────────────

# Recurring costs
SUBSCRIPTION_UNUSED_DAYS = 30           # flag if unused > 30 days
SUBSCRIPTION_NOT_REVIEWED_DAYS = 90     # flag if not reviewed > 90 days
HIGH_VALUE_SUBSCRIPTION_INR = 5000      # medium severity threshold

# Tax
TDS_CRITICAL_DAYS_BEFORE_DUE = 3       # critical if due within 3 days
GST_MEDIUM_DAYS_BEFORE_DUE = 5         # medium if due within 5 days
PF_OVERDUE_CRITICAL_DAYS = 0           # critical if overdue by even 1 day

# Payroll
ESI_THRESHOLD_INR = 21000              # contractor monthly gross above this → ESI applicable
PF_ENROLLMENT_WINDOW_DAYS = 30         # new joiner must be enrolled within 30 days
FFS_DELAYED_CRITICAL_DAYS = 15         # F&F overdue > 15 days → critical
FFS_DELAYED_MEDIUM_DAYS = 0            # F&F delayed at all → medium

# SLA hours per severity
SLA_HOURS = {
    Severity.CRITICAL: 0,
    Severity.MEDIUM: 48,
    Severity.LOW: 72,
}
