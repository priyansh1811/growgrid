"""Pre-pipeline Clarification Agent — asks follow-up questions for better context.

Runs before the main pipeline. Uses an LLM to analyse form inputs and optionally
return 1–3 follow-up questions. After the user answers, refine() can suggest
updates to goal or risk tolerance for building the PlanRequest.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from growgrid_core.tools.llm_client import BaseLLMClient, get_llm_client
from growgrid_core.utils.enums import Goal, RiskLevel

logger = logging.getLogger(__name__)

_MAX_SUGGESTED_OPTIONS = 5
VALID_GOAL_VALUES = {g.value for g in Goal}
VALID_RISK_VALUES = {r.value for r in RiskLevel}


# ── Response types ──────────────────────────────────────────────────────────


class ClarificationQuestion(BaseModel):
    """A single follow-up question for the user."""

    id: str = Field(..., description="Unique id for this question")
    question: str = Field(..., description="Question text to show the user")
    suggested_options: list[str] | None = Field(
        default=None,
        description="Optional list of choices (e.g. goal or risk options)",
    )


class ClarificationResult(BaseModel):
    """Result of analysing form inputs — whether to ask follow-ups."""

    clarification_needed: bool = Field(
        ...,
        description="True if the agent suggests asking 1–3 follow-up questions",
    )
    questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="Follow-up questions to show the user (if clarification_needed)",
    )
    message: str | None = Field(
        default=None,
        description="Optional short message explaining why clarification is suggested",
    )


class RefinementResult(BaseModel):
    """Suggested updates to apply when building PlanRequest after user answers."""

    suggested_goal: str | None = Field(
        default=None,
        description="Goal enum value (e.g. MAXIMIZE_PROFIT) if the LLM suggests a change",
    )
    suggested_risk_tolerance: str | None = Field(
        default=None,
        description="RiskLevel enum value if the LLM suggests a change",
    )
    user_context: str | None = Field(
        default=None,
        description="Short summary of user context for downstream agents (optional)",
    )


def _ensure_dict(obj: Any) -> dict[str, Any]:
    """Coerce LLM output into a dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        try:
            data = json.loads(obj)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


# ── Prompt templates ───────────────────────────────────────────────────────

_CLARIFICATION_SYSTEM = """You are an agricultural planning assistant for Indian farmers. The user has filled a form with: location, land area, water availability, irrigation source, budget, labour, primary goal, time horizon, and risk tolerance.

Your job is to decide if 1–3 short follow-up questions would help provide better recommendations. Ask only when:
- The goal is ambiguous (e.g. they want profit but also stability)
- There is a tension (e.g. very low budget + maximize profit, or short horizon + orchard)
- Context would help (e.g. first-time farmer, trial plot vs full scale, seasonal vs year-round irrigation)

Do NOT ask more than 3 questions. Do NOT ask for information already in the form. Prefer multiple-choice style when possible (suggested_options). Use stable, URL-friendly question ids (e.g. goal_ambiguity, trial_plot, irrigation_context).

Return a JSON object with exactly these keys:
{
  "clarification_needed": true or false,
  "message": "Optional one sentence why you are asking (or null if clarification_needed is false)",
  "questions": [
    {
      "id": "short_snake_case_id",
      "question": "Clear, friendly question text?",
      "suggested_options": ["Option A", "Option B"] or null
    }
  ]
}
If clarification_needed is false, questions must be an empty array. suggested_options must have at most 5 items. Use only the keys above."""

_REFINEMENT_SYSTEM = """You are an agricultural planning assistant. The user has answered follow-up clarification questions. Based on their original form and these answers, suggest any updates to improve the plan request.

Return a JSON object with these keys (use null if no change suggested):
{
  "suggested_goal": "MAXIMIZE_PROFIT | STABLE_INCOME | WATER_SAVING | FAST_ROI or null",
  "suggested_risk_tolerance": "LOW | MED | HIGH or null",
  "user_context": "One optional sentence summarizing context for downstream recommendations, or null"
}
Only suggest goal or risk_tolerance if the user's answers clearly indicate a different preference. Keep user_context brief and actionable."""


# ── Agent ──────────────────────────────────────────────────────────────────


class ClarificationAgent:
    """Analyses form inputs and optionally returns follow-up questions; refines after answers."""

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self._llm = llm_client

    def analyze(self, form_inputs: dict[str, Any]) -> ClarificationResult:
        """Decide if follow-up questions are needed based on the form.

        Args:
            form_inputs: Dict with keys like location, land_area_acres,
                water_availability, irrigation_source, budget_total_inr,
                labour_availability, goal, time_horizon_years, risk_tolerance
                (values as strings/numbers as in the UI).

        Returns:
            ClarificationResult with clarification_needed and questions (if any).
        """
        llm = get_llm_client(self._llm)
        user_prompt = (
            "Current form inputs:\n"
            + json.dumps(form_inputs, indent=2)
            + "\n\nShould we ask any follow-up questions? Return the JSON object."
        )
        try:
            raw = llm.complete(_CLARIFICATION_SYSTEM, user_prompt)
            data = _ensure_dict(raw)
        except Exception as e:
            logger.warning("Clarification analysis failed: %s", e)
            return ClarificationResult(
                clarification_needed=False,
                questions=[],
                message=None,
            )

        clarification_needed = bool(data.get("clarification_needed", False))
        message = data.get("message")
        questions: list[ClarificationQuestion] = []
        for q in data.get("questions") or []:
            q = _ensure_dict(q)
            if not q.get("id") or not q.get("question"):
                continue
            opts = None
            if isinstance(q.get("suggested_options"), list):
                opts = [
                    str(o).strip()
                    for o in q["suggested_options"][:_MAX_SUGGESTED_OPTIONS]
                    if o and str(o).strip()
                ]
                opts = opts if opts else None
            questions.append(
                ClarificationQuestion(
                    id=str(q["id"]).strip(),
                    question=str(q["question"]).strip(),
                    suggested_options=opts,
                )
            )

        result = ClarificationResult(
            clarification_needed=clarification_needed and len(questions) > 0,
            questions=questions[:3],
            message=message,
        )
        if result.clarification_needed:
            logger.info(
                "Clarification requested: %d question(s), message=%s",
                len(result.questions),
                result.message or "(none)",
            )
        return result

    def refine(
        self,
        form_inputs: dict[str, Any],
        answers: list[dict[str, str]],
    ) -> RefinementResult:
        """Suggest updates to goal/risk/context after the user has answered clarification questions.

        Args:
            form_inputs: Same dict as passed to analyze().
            answers: List of {"question_id": "...", "answer": "..."}.

        Returns:
            RefinementResult with suggested_goal, suggested_risk_tolerance, user_context (optional).
        """
        llm = get_llm_client(self._llm)
        user_prompt = (
            "Original form inputs:\n"
            + json.dumps(form_inputs, indent=2)
            + "\n\nUser answers to clarification questions:\n"
            + json.dumps(answers, indent=2)
            + "\n\nSuggest any updates (goal, risk_tolerance, user_context). Return the JSON object."
        )
        try:
            raw = llm.complete(_REFINEMENT_SYSTEM, user_prompt)
            data = _ensure_dict(raw)
        except Exception as e:
            logger.warning("Clarification refine failed: %s", e)
            return RefinementResult()

        suggested_goal = data.get("suggested_goal")
        suggested_risk_tolerance = data.get("suggested_risk_tolerance")
        user_context = data.get("user_context")

        if suggested_goal is not None:
            suggested_goal = str(suggested_goal).strip().upper()
            if suggested_goal not in VALID_GOAL_VALUES:
                logger.warning("Refinement suggested invalid goal %r; ignoring", suggested_goal)
                suggested_goal = None
        if suggested_risk_tolerance is not None:
            suggested_risk_tolerance = str(suggested_risk_tolerance).strip().upper()
            if suggested_risk_tolerance not in VALID_RISK_VALUES:
                logger.warning(
                    "Refinement suggested invalid risk_tolerance %r; ignoring",
                    suggested_risk_tolerance,
                )
                suggested_risk_tolerance = None
        if user_context is not None:
            user_context = str(user_context).strip() or None

        if suggested_goal or suggested_risk_tolerance:
            logger.info(
                "Refinement overrides: goal=%s, risk_tolerance=%s",
                suggested_goal,
                suggested_risk_tolerance,
            )

        return RefinementResult(
            suggested_goal=suggested_goal or None,
            suggested_risk_tolerance=suggested_risk_tolerance or None,
            user_context=user_context,
        )
