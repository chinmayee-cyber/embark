"""
Advisor AI Agent
─────────────────
The only LLM-powered component in the system.
Uses Agno with Gemini to generate structured recommendations
for each CRITICAL and MEDIUM escalation.

Key design decisions based on Gemini + Agno constraints:
- No tools are used on the agent (Gemini cannot use tools + response_model simultaneously)
- Structured output is enforced via system prompt (JSON-only instruction)
- response_model is NOT used to avoid the Gemini tools/structured-output conflict
- JSON is parsed manually from the response string with error handling
"""

import json
import re
from datetime import date
from typing import List

from agno.agent import Agent
from agno.models.google import Gemini

from src.models.schemas import EscalationEvent, Recommendation
from src.models.constants import Severity
from src.agent.prompts import ADVISOR_SYSTEM_PROMPT, build_advisor_prompt


class AdvisorAgent:
    """
    AI agent that generates one Recommendation per CRITICAL or MEDIUM escalation.
    LOW severity escalations receive a templated recommendation without an LLM call.
    """

    def __init__(self, model_id: str = "gemini-2.0-flash", reference_date: date | None = None):
        self.today = reference_date or date.today()
        self.api_calls_made = 0

        self.agent = Agent(
            model=Gemini(id=model_id),
            description="Financial escalation advisor for Indian startups",
            instructions=[ADVISOR_SYSTEM_PROMPT],
            markdown=False,
        )

    # ─── Cross-domain detection ───────────────────────────────────────────────

    def _build_cross_domain_index(
        self, escalations: List[EscalationEvent]
    ) -> dict[str, List[str]]:
        """
        Build a lookup: vendor_id/worker_id → list of source_ids that share that key.
        Used to detect when a single vendor or worker appears across multiple domains.
        """
        vendor_index: dict[str, List[str]] = {}
        worker_index: dict[str, List[str]] = {}

        for e in escalations:
            if e.vendor_id:
                vendor_index.setdefault(e.vendor_id, []).append(e.source_id)
            if e.worker_id:
                worker_index.setdefault(e.worker_id, []).append(e.source_id)

        # Merge into a single source_id → linked_ids map
        cross_domain: dict[str, List[str]] = {}
        for key, ids in {**vendor_index, **worker_index}.items():
            if len(ids) > 1:
                for sid in ids:
                    linked = [i for i in ids if i != sid]
                    cross_domain.setdefault(sid, []).extend(linked)

        return cross_domain

    def _build_cross_domain_context(
        self,
        escalation: EscalationEvent,
        all_escalations: List[EscalationEvent],
        cross_domain_map: dict[str, List[str]],
    ) -> str:
        """
        Returns a readable summary of cross-domain links for the prompt.
        """
        linked_ids = cross_domain_map.get(escalation.source_id, [])
        if not linked_ids:
            return ""

        lines = []
        for sid in linked_ids:
            linked = next((e for e in all_escalations if e.source_id == sid), None)
            if linked:
                lines.append(
                    f"- {sid} [{linked.domain}] {linked.trigger_type}: {linked.description[:120]}"
                )
        return "\n".join(lines)

    # ─── LLM call ─────────────────────────────────────────────────────────────

    def _call_llm(self, prompt: str, source_id: str) -> dict:
        """
        Calls the Agno/Gemini agent and parses the JSON response.
        Returns a dict on success or a fallback dict with api_error=True on failure.
        """
        try:
            self.api_calls_made += 1
            response = self.agent.run(prompt)
            raw_text = response.content if response and response.content else ""

            # Strip any accidental markdown fences
            cleaned = re.sub(r"```(?:json)?|```", "", raw_text).strip()

            parsed = json.loads(cleaned)
            parsed["api_error"] = False
            return parsed

        except json.JSONDecodeError as e:
            return {
                "source_id": source_id,
                "action": "Manual review required — LLM response could not be parsed.",
                "financial_exposure_inr": 0,
                "owner": "Finance Lead",
                "deadline": self.today.isoformat(),
                "cross_domain_flag": False,
                "linked_records": [],
                "reasoning": f"JSON parse error: {str(e)[:100]}",
                "api_error": True,
            }
        except Exception as e:
            return {
                "source_id": source_id,
                "action": "Manual review required — API call failed.",
                "financial_exposure_inr": 0,
                "owner": "Finance Lead",
                "deadline": self.today.isoformat(),
                "cross_domain_flag": False,
                "linked_records": [],
                "reasoning": f"API error: {str(e)[:100]}",
                "api_error": True,
            }

    # ─── Templated LOW recommendation (no LLM call) ───────────────────────────

    def _template_low(
        self,
        escalation: EscalationEvent,
        cross_domain_map: dict[str, List[str]],
    ) -> Recommendation:
        linked = cross_domain_map.get(escalation.source_id, [])
        return Recommendation(
            source_id=escalation.source_id,
            action=f"Schedule review of {escalation.source_id} ({escalation.trigger_type}) "
                   f"within 72 hours. Assign an owner and decide: cancel, renew, or document.",
            financial_exposure_inr=escalation.amount_inr or 0.0,
            owner=escalation.owner.value,
            deadline=(self.today.isoformat()),
            cross_domain_flag=bool(linked),
            linked_records=linked,
            reasoning=(
                "Low severity hygiene issue. No immediate financial penalty, "
                "but unresolved items accumulate into material cost leakage."
            ),
            api_error=False,
        )

    # ─── Main entry point ─────────────────────────────────────────────────────

    def run(self, escalations: List[EscalationEvent]) -> List[Recommendation]:
        cross_domain_map = self._build_cross_domain_index(escalations)
        recommendations: List[Recommendation] = []

        for escalation in escalations:
            if escalation.severity == Severity.LOW:
                recommendations.append(self._template_low(escalation, cross_domain_map))
                continue

            # Build prompt for CRITICAL and MEDIUM
            cross_ctx = self._build_cross_domain_context(
                escalation, escalations, cross_domain_map
            )
            prompt = build_advisor_prompt(
                escalation={
                    "source_id": escalation.source_id,
                    "domain": escalation.domain,
                    "severity": escalation.severity.value,
                    "trigger_type": escalation.trigger_type,
                    "description": escalation.description,
                    "amount_inr": escalation.amount_inr,
                    "owner": escalation.owner.value,
                    "sla_hours": escalation.sla_hours,
                },
                cross_domain_context=cross_ctx,
                today=self.today.isoformat(),
            )

            raw = self._call_llm(prompt, escalation.source_id)

            # Merge cross-domain data detected by the rule engine
            # (rule engine is more reliable than LLM for structural linkage)
            linked = cross_domain_map.get(escalation.source_id, [])
            if linked:
                raw["cross_domain_flag"] = True
                raw["linked_records"] = list(set(raw.get("linked_records", []) + linked))

            recommendations.append(Recommendation(
                source_id=raw.get("source_id", escalation.source_id),
                action=raw.get("action", "Review required"),
                financial_exposure_inr=float(raw.get("financial_exposure_inr", 0)),
                owner=raw.get("owner", escalation.owner.value),
                deadline=raw.get("deadline", self.today.isoformat()),
                cross_domain_flag=raw.get("cross_domain_flag", False),
                linked_records=raw.get("linked_records", []),
                reasoning=raw.get("reasoning", ""),
                api_error=raw.get("api_error", False),
            ))

        return recommendations
