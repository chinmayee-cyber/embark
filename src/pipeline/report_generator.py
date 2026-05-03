"""
Leadership HTML Report Generator
─────────────────────────────────
Renders a self-contained HTML executive report from a PipelineOutput.

The output file is intentionally a single HTML document with all CSS
inlined so it can be emailed, opened in any browser, and printed
to PDF (Ctrl+P) without any external assets.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.models.schemas import EscalationEvent, PipelineOutput, Recommendation


_TEMPLATE_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "report.html.j2"

_DOMAIN_LABELS = {
    "recurring_cost": "Recurring Costs",
    "tax": "Tax",
    "payroll": "Payroll",
}

_SEVERITY_ORDER = {"CRITICAL": 0, "MEDIUM": 1, "LOW": 2}


def _format_inr(value: Optional[float]) -> str:
    """Format an INR amount using Indian digit grouping (e.g. 12,34,567).

    Returns "-" for None values so the template can render gracefully.
    """
    if value is None:
        return "-"
    try:
        amount = int(round(float(value)))
    except (TypeError, ValueError):
        return "-"

    sign = "-" if amount < 0 else ""
    s = str(abs(amount))

    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        # group remaining digits in pairs from the right
        chunks = []
        while len(rest) > 2:
            chunks.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            chunks.append(rest)
        grouped = ",".join(reversed(chunks)) + "," + last3

    return f"{sign}Rs {grouped}"


def _domain_label(domain: str) -> str:
    return _DOMAIN_LABELS.get(domain, domain.replace("_", " ").title())


def _deadline_sort_key(rec: Optional[Recommendation], esc: EscalationEvent) -> tuple:
    """Sort by deadline ascending; items missing a deadline go last."""
    if rec and rec.deadline:
        return (0, rec.deadline, esc.source_id)
    return (1, "", esc.source_id)


def _build_items(
    escalations: list[EscalationEvent],
    recs_by_id: dict[str, Recommendation],
) -> list[dict]:
    items = []
    for esc in escalations:
        rec = recs_by_id.get(esc.source_id)
        items.append({"escalation": esc, "recommendation": rec})
    items.sort(
        key=lambda it: _deadline_sort_key(it["recommendation"], it["escalation"])
    )
    return items


def _resolve_exposure(esc: EscalationEvent, rec: Optional[Recommendation]) -> float:
    """Best estimate of financial exposure for a single item.

    Prefers the advisor's `financial_exposure_inr` when it is non-zero,
    otherwise falls back to the underlying record amount (`amount_inr`).
    """
    if rec is not None and rec.financial_exposure_inr:
        return float(rec.financial_exposure_inr)
    return float(esc.amount_inr or 0.0)


def _domain_breakdown(items: list[dict]) -> list[dict]:
    counts: dict[str, dict] = {}
    for it in items:
        esc: EscalationEvent = it["escalation"]
        rec: Optional[Recommendation] = it["recommendation"]
        bucket = counts.setdefault(esc.domain, {"count": 0, "exposure": 0.0})
        bucket["count"] += 1
        bucket["exposure"] += _resolve_exposure(esc, rec)

    rows = [
        {"label": _domain_label(domain), "count": v["count"], "exposure": v["exposure"]}
        for domain, v in counts.items()
    ]
    rows.sort(key=lambda r: r["exposure"], reverse=True)
    return rows


def _owner_breakdown(items: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for it in items:
        owner = it["escalation"].owner
        owner_str = owner.value if hasattr(owner, "value") else str(owner)
        counts[owner_str] = counts.get(owner_str, 0) + 1
    rows = [{"label": label, "count": c} for label, c in counts.items()]
    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows


def _total_exposure(items: list[dict]) -> float:
    return sum(
        _resolve_exposure(it["escalation"], it["recommendation"]) for it in items
    )


def generate_html_report(output: PipelineOutput, report_path: Path) -> Path:
    """Render the executive HTML report and write it to ``report_path``.

    Returns the path written.
    """
    recs_by_id: dict[str, Recommendation] = {
        r.source_id: r for r in output.recommendations
    }
    all_items = _build_items(output.escalations, recs_by_id)

    def severity_value(it: dict) -> str:
        sev = it["escalation"].severity
        return sev.value if hasattr(sev, "value") else str(sev)

    critical_items = [it for it in all_items if severity_value(it) == "CRITICAL"]
    medium_items = [it for it in all_items if severity_value(it) == "MEDIUM"]
    low_items = [it for it in all_items if severity_value(it) == "LOW"]

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["format_inr"] = _format_inr
    env.globals["domain_label"] = _domain_label
    env.globals["resolve_exposure"] = _resolve_exposure

    template = env.get_template(_TEMPLATE_NAME)
    html = template.render(
        output=output,
        critical_items=critical_items,
        medium_items=medium_items,
        low_items=low_items,
        domain_breakdown=_domain_breakdown(all_items),
        owner_breakdown=_owner_breakdown(all_items),
        total_exposure=_total_exposure(all_items),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")
    return report_path
