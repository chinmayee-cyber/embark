"""
Data loader
────────────
Loads and validates the three synthetic JSON datasets into Pydantic models.
"""

import json
from pathlib import Path
from typing import List

from src.models.schemas import RecurringCost, TaxObligation, PayrollRecord


DATA_DIR = Path(__file__).parent.parent.parent / "data"


def load_recurring_costs(path: Path | None = None) -> List[RecurringCost]:
    path = path or DATA_DIR / "recurring_costs.json"
    raw = json.loads(path.read_text())
    return [RecurringCost(**item) for item in raw]


def load_tax_obligations(path: Path | None = None) -> List[TaxObligation]:
    path = path or DATA_DIR / "tax_obligations.json"
    raw = json.loads(path.read_text())
    return [TaxObligation(**item) for item in raw]


def load_payroll_records(path: Path | None = None) -> List[PayrollRecord]:
    path = path or DATA_DIR / "payroll_records.json"
    raw = json.loads(path.read_text())
    return [PayrollRecord(**item) for item in raw]
