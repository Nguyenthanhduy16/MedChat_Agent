"""LLM-based Evidence Checker.

Verifies retrieved contexts before generation:
- Filters wrong-entity or wrong-field contexts via LLM judgement
- Assesses whether remaining evidence is sufficient to answer
- Returns structured JSON result without generating an answer
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Literal

from core.models import EvidenceItem
from core.llm import ChatModel
from core.text import accent_fold

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------
# Output model
# -----------------------------------------------------------------

EvidenceStatusLiteral = Literal["complete", "partial", "incomplete"]


@dataclass
class EvidenceCheckResult:
    """Result of LLM evidence verification."""

    kept_context_ids: list[str]
    """IDs of contexts that passed the check."""

    evidence_status: EvidenceStatusLiteral
    """'complete' | 'partial' | 'incomplete'"""

    missing_fields: list[str]
    """Required fields with no supporting context."""

    notes: str = ""
    """Brief LLM explanation (for logging/debugging)."""

    fallback_used: bool = False
    """True when the LLM call failed and rule-based fallback was applied."""


# -----------------------------------------------------------------
# Prompt builder
# -----------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an evidence quality checker for a pharmacy information system.

Your task: examine each retrieved context and decide which ones are relevant to the question.

STRICT RULES:
1. Only keep a context if its title/content clearly relates to the main entity ({main_entity}).
2. Do NOT keep contexts about other drugs/substances, UNLESS the intent is "interaction" \
AND the question explicitly mentions that other drug.
3. Each required field must have at least one supporting context; if any required field \
has no context, set that field in "missing_fields".
4. evidence_status:
   - "complete"   → every required field has at least one correct context
   - "partial"    → some required fields covered but not all, OR evidence is thin
   - "incomplete" → no required field is covered, or all contexts are about wrong entity
5. NEVER generate or infer medical information yourself. Only evaluate contexts.
6. Output ONLY valid JSON with the following schema (no markdown, no explanation outside JSON):

{{
  "kept_context_ids": ["<id>", ...],
  "evidence_status": "complete" | "partial" | "incomplete",
  "missing_fields": ["<field>", ...],
  "notes": "<brief reason>"
}}
"""

_USER_TEMPLATE = """\
Question: {question}
Main entity (drug / substance): {main_entity}
Intent(s): {intents}
Required field(s): {required_fields}

Retrieved contexts:
{context_block}

Evaluate each context and return ONLY the JSON result.
"""


def _build_context_block(items_with_ids: list[tuple[str, EvidenceItem]], max_chars: int = 300) -> str:
    lines: list[str] = []
    for ctx_id, item in items_with_ids:
        snippet = item.text[:max_chars].replace("\n", " ")
        item_field = item.metadata.get("field", "unknown")
        lines.append(
            f"[{ctx_id}] title={item.title!r} field={item_field!r} doc={item.url or item.id!r}\n"
            f"    snippet: {snippet}"
        )
    return "\n\n".join(lines)


# -----------------------------------------------------------------
# Checker class
# -----------------------------------------------------------------

class LLMEvidenceChecker:
    """Calls a fast LLM to verify evidence quality before generation."""

    def __init__(self, chat_model: ChatModel, timeout_seconds: float = 12.0) -> None:
        self.chat_model = chat_model
        self.timeout_seconds = timeout_seconds

    async def check(
        self,
        question: str,
        main_entity: str,
        intents: list[str],
        required_fields: list[str],
        facet_results: dict[str, list[EvidenceItem]],
    ) -> EvidenceCheckResult:
        """Run LLM evidence check and return a structured result.

        Falls back to keeping all context IDs (with status='partial') when
        the LLM call fails or returns unparseable JSON.
        """
        # Flatten facet_results with stable IDs so the LLM can reference them
        items_with_ids: list[tuple[str, EvidenceItem]] = []
        for facet_id, items in facet_results.items():
            for idx, item in enumerate(items):
                ctx_id = f"{facet_id}:{idx}"
                items_with_ids.append((ctx_id, item))

        if not items_with_ids:
            return EvidenceCheckResult(
                kept_context_ids=[],
                evidence_status="incomplete",
                missing_fields=required_fields,
                notes="No contexts to evaluate.",
            )

        system = _SYSTEM_PROMPT.format(main_entity=main_entity or "(unknown)")
        user = _USER_TEMPLATE.format(
            question=question,
            main_entity=main_entity or "(unknown)",
            intents=", ".join(intents) if intents else "(unknown)",
            required_fields=", ".join(required_fields) if required_fields else "(any)",
            context_block=_build_context_block(items_with_ids),
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            raw = await self.chat_model.generate(messages, timeout_seconds=self.timeout_seconds)
            result = self._parse_json(raw)
            logger.info(
                "evidence_checker.llm status=%s kept=%s missing=%s",
                result.evidence_status,
                len(result.kept_context_ids),
                result.missing_fields,
            )
            return result
        except Exception as exc:
            logger.warning("evidence_checker.llm failed (fallback to keep-all): %s", exc)
            all_ids = [ctx_id for ctx_id, _ in items_with_ids]
            return EvidenceCheckResult(
                kept_context_ids=all_ids,
                evidence_status="partial",
                missing_fields=[],
                notes=f"LLM check failed: {exc}",
                fallback_used=True,
            )

    @staticmethod
    def _parse_json(raw: str) -> EvidenceCheckResult:
        # Strip markdown fences if present
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"No JSON object found in LLM response: {text[:200]!r}")

        data = json.loads(text[start : end + 1])
        status = data.get("evidence_status", "partial")
        if status not in ("complete", "partial", "incomplete"):
            status = "partial"

        return EvidenceCheckResult(
            kept_context_ids=[str(x) for x in data.get("kept_context_ids", [])],
            evidence_status=status,
            missing_fields=[str(x) for x in data.get("missing_fields", [])],
            notes=str(data.get("notes", "")),
        )


# -----------------------------------------------------------------
# Helper: apply checker result back onto facet_results
# -----------------------------------------------------------------

def apply_evidence_check(
    facet_results: dict[str, list[EvidenceItem]],
    check_result: EvidenceCheckResult,
) -> dict[str, list[EvidenceItem]]:
    """Return a new facet_results dict containing only the contexts the LLM approved.

    Falls back to the original per-facet list when the LLM approved no items for
    that facet (safety net — avoids silently blocking all evidence for a facet).
    """
    if check_result.fallback_used:
        return facet_results  # LLM failed; keep everything

    approved: set[str] = set(check_result.kept_context_ids)

    filtered: dict[str, list[EvidenceItem]] = {}
    for facet_id, items in facet_results.items():
        passing = [
            item
            for idx, item in enumerate(items)
            if f"{facet_id}:{idx}" in approved
        ]
        # Safety fallback: if checker removed everything for a facet, keep original
        filtered[facet_id] = passing if passing else items

    return filtered
