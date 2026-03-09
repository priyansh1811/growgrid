"""Agent 5 — Agronomist Expert (Verifier + Short Grow Guide).

Uses LLM reasoning + Tavily web search to:
 - verify practice/crop suitability
 - detect conflicts
 - suggest adjustments
 - generate a grow guide per crop

This is the ONLY agent that calls external APIs (LLM, Tavily).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.tools.llm_client import BaseLLMClient, get_llm_client
from growgrid_core.tools.tavily_client import BaseTavilyClient, get_tavily_client
from growgrid_core.tools.tool_cache import ToolCache
from growgrid_core.utils.enums import ConflictLevel
from growgrid_core.utils.types import (
    AgronomistVerification,
    CropPortfolioEntry,
    CropScore,
    EvidenceCard,
    GrowGuide,
    PlanRequest,
    PracticeScore,
    ValidatedProfile,
)


logger = logging.getLogger(__name__)

# Month N: ... pattern for grow guide timeline
_MONTH_LINE_PATTERN = re.compile(r"^\s*Month\s+(\d+)\s*:\s*(.*)$", re.IGNORECASE)


def _normalize_monthly_timeline(raw: list[str]) -> list[str]:
    """Enforce 'Month 1: ...', 'Month 2: ...' format. Re-number or prefix non-matching lines."""
    result: list[str] = []
    for i, line in enumerate(raw, start=1):
        s = (line or "").strip()
        if not s:
            result.append(f"Month {i}: (no description)")
            continue
        m = _MONTH_LINE_PATTERN.match(s)
        if m:
            result.append(f"Month {m.group(1)}: {m.group(2).strip()}")
        else:
            result.append(f"Month {i}: {s}")
    return result if result else ["Month 1: Consult local agricultural calendar"]


def _ensure_dict(obj: Any) -> dict[str, Any]:
    """Coerce LLM output into a dict.

    Some LLM clients return already-parsed dicts; others return JSON strings.
    """
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


# ── Prompt templates ─────────────────────────────────────────────────────

_EVIDENCE_EXTRACTION_SYSTEM = """You are an agricultural expert. Given web search results about a crop and farming practice, extract structured evidence.

Return a JSON object with these keys:
{
  "sowing_window": "string — best sowing/planting months for the location",
  "climate_suitability": "string — climate/temperature suitability notes",
  "irrigation_notes": "string — irrigation intensity and method notes",
  "major_pests": "string — top pests and diseases",
  "time_to_harvest": "string — months to first income/harvest",
  "hard_warnings": "string — any 'not recommended if...' warnings, or empty string"
}
Only use information from the provided search results. Be concise."""

_CONFLICT_DETECTION_SYSTEM = """You are an agricultural verification expert. Compare the evidence against the current recommendation and constraints.

For each claim, classify the conflict level as one of:
- NO_ISSUE: evidence supports the recommendation
- MINOR_VARIATION: small differences that don't affect feasibility
- CONTEXT_DEPENDENT: suitability depends on specific conditions (e.g., variety, irrigation method)
- MAJOR_CONFLICT: evidence contradicts the recommendation on a hard constraint

Return a JSON object:
{
  "claims": [
    {
      "claim": "string — the claim being verified",
      "conflict_level": "NO_ISSUE|MINOR_VARIATION|CONTEXT_DEPENDENT|MAJOR_CONFLICT",
      "explanation": "string — brief explanation",
      "required_action": "string — action needed if any, or empty"
    }
  ],
  "overall_confidence": 0.0 to 1.0
}"""

_GROW_GUIDE_SYSTEM = """You are an Indian agricultural advisor. Generate a concise grow guide for a specific crop.

Return a JSON object with these exact keys:
{
  "sowing_window": "string — optimal sowing/planting window for the location",
  "monthly_timeline": ["Month 1: ...", "Month 2: ...", ...],
  "land_prep": "string — land preparation and sowing/transplant method",
  "irrigation_rules": "string — irrigation thumb rules by growth stage",
  "fertilizer_plan": "string — simple NPK stages",
  "pest_prevention": ["point 1", "point 2", "point 3"],
  "harvest_notes": "string — harvesting and post-harvest handling",
  "why_recommended": "string — one line on why this crop is recommended",
  "when_not_recommended": "string — one line on when NOT to grow this crop"
}
Be practical and India-specific. Keep it short and actionable."""


class AgronomistVerifierAgent(BaseAgent):
    """Verify recommendations via LLM + Tavily, generate grow guides."""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        tavily_client: BaseTavilyClient | None = None,
        cache: ToolCache | None = None,
    ) -> None:
        self._llm = llm_client
        self._tavily = tavily_client
        self._cache = cache

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        profile: ValidatedProfile = state["validated_profile"]
        selected_practice: PracticeScore = state["selected_practice"]
        crop_portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]
        crop_ranking: list[CropScore] = state.get("crop_ranking", [])

        llm = get_llm_client(self._llm)
        tavily = get_tavily_client(self._tavily)
        cache = self._cache

        # Early exit if no practice / crops
        if selected_practice.eliminated or not crop_portfolio:
            state["agronomist_verification"] = AgronomistVerification(
                confidence_score=0.0,
                warnings=["No practice or crops to verify."],
            )
            state["grow_guides"] = []
            return state

        # ── Phase 1: Build claims ────────────────────────────────────
        user_context = getattr(request, "user_context", None) or None
        claims = self._build_claims(profile, selected_practice, crop_portfolio, user_context)

        # ── Phase 2: Tavily search (with caching) ───────────────────
        all_evidence: list[EvidenceCard] = []
        all_citations: list[str] = []

        for entry in crop_portfolio:
            search_results = self._search_with_cache(
                tavily, cache, profile, selected_practice, entry
            )

            crop_citations: list[str] = []
            for r in search_results:
                url = r.get("url") or ""
                if url:
                    crop_citations.append(url)
                    all_citations.append(url)

            # ── Phase 3: Evidence extraction (LLM) ──────────────────
            evidence_data = self._extract_evidence(llm, entry, search_results)

            # ── Phase 4: Conflict detection (LLM) ───────────────────
            conflict_data = self._detect_conflicts(
                llm, claims, evidence_data, profile, entry
            )

            conflict_data = _ensure_dict(conflict_data)
            for cd in conflict_data.get("claims", []) or []:
                cd = _ensure_dict(cd)
                all_evidence.append(
                    EvidenceCard(
                        claim=cd.get("claim", ""),
                        source_url=crop_citations[0] if crop_citations else "",
                        snippet=cd.get("explanation", ""),
                        conflict_level=self._parse_conflict_level(
                            cd.get("conflict_level", "NO_ISSUE")
                        ),
                    )
                )

        # ── Phase 5: Adjustment policy ──────────────────────────────
        verified_portfolio, warnings, actions = self._apply_adjustments(
            crop_portfolio, crop_ranking, all_evidence
        )

        # ── Phase 6: Grow guide generation ──────────────────────────
        grow_guides: list[GrowGuide] = []
        for entry in verified_portfolio:
            guide = self._generate_grow_guide(llm, profile, selected_practice, entry, user_context)
            grow_guides.append(guide)

        # Compute confidence
        confidence = self._compute_confidence(all_evidence)

        verification = AgronomistVerification(
            verified_practice=selected_practice,
            verified_crop_portfolio=verified_portfolio,
            confidence_score=confidence,
            warnings=warnings,
            required_actions=actions,
            citations=list(set(all_citations)),
            evidence_cards=all_evidence,
        )

        state["agronomist_verification"] = verification
        state["grow_guides"] = grow_guides
        return state

    # ── Phase helpers ────────────────────────────────────────────────

    @staticmethod
    def _build_claims(
        profile: ValidatedProfile,
        practice: PracticeScore,
        portfolio: list[CropPortfolioEntry],
        user_context: str | None = None,
    ) -> list[str]:
        claims = [
            f"Practice '{practice.practice_name}' is feasible for "
            f"budget {profile.budget_per_acre:.0f} INR/acre, "
            f"water={profile.water_availability.value}, "
            f"labour={profile.labour_availability.value}."
        ]
        if user_context and user_context.strip():
            claims.append(f"User context: {user_context.strip()}")
        for entry in portfolio:
            claims.append(
                f"Crop '{entry.crop_name}' is suitable in "
                f"{profile.location} with water={profile.water_availability.value} "
                f"and horizon={profile.horizon_months} months."
            )
        return claims

    @staticmethod
    def _search_with_cache(
        tavily: BaseTavilyClient,
        cache: ToolCache | None,
        profile: ValidatedProfile,
        practice: PracticeScore,
        entry: CropPortfolioEntry,
    ) -> list[dict[str, Any]]:
        """Search Tavily with optional caching."""
        cache_key = f"{profile.location}|{practice.practice_code}|{entry.crop_id}|v1"

        if cache is not None:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        queries = [
            f"{entry.crop_name} cultivation package of practices {profile.location} India",
            f"{entry.crop_name} sowing time {profile.location} {practice.practice_name}",
            f"{entry.crop_name} irrigation requirement water need India",
            f"{entry.crop_name} major pests diseases India management",
        ]

        results: list[dict[str, Any]] = []
        for q in queries:
            try:
                results.extend(tavily.search(q, max_results=3))
            except Exception as e:
                logger.warning("Tavily search failed: %s", e)

        if cache is not None and results:
            cache.set(cache_key, results)

        return results

    @staticmethod
    def _extract_evidence(
        llm: BaseLLMClient,
        entry: CropPortfolioEntry,
        search_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Use LLM to extract structured evidence from search results."""
        snippets = "\n\n".join(
            f"Source: {r.get('title', 'N/A')}\nURL: {r.get('url', '')}\n{r.get('content', '')}"
            for r in search_results[:6]
        )
        if not snippets:
            return {
                "sowing_window": "Unknown",
                "climate_suitability": "Unknown",
                "irrigation_notes": "Unknown",
                "major_pests": "Unknown",
                "time_to_harvest": "Unknown",
                "hard_warnings": "",
            }

        user_prompt = (
            f"Crop: {entry.crop_name}\n\n"
            f"Search results:\n{snippets}\n\n"
            "Extract structured evidence as JSON."
        )

        try:
            return _ensure_dict(llm.complete(_EVIDENCE_EXTRACTION_SYSTEM, user_prompt))
        except Exception as e:
            logger.warning("Evidence extraction failed: %s", e)
            return {"hard_warnings": "", "sowing_window": "Unknown"}

    @staticmethod
    def _detect_conflicts(
        llm: BaseLLMClient,
        claims: list[str],
        evidence: dict[str, Any],
        profile: ValidatedProfile,
        entry: CropPortfolioEntry,
    ) -> dict[str, Any]:
        """Use LLM to detect conflicts between evidence and recommendations."""
        user_prompt = (
            "Claims to verify:\n"
            + "\n".join(f"- {c}" for c in claims)
            + f"\n\nEvidence for {entry.crop_name}:\n{json.dumps(evidence, indent=2)}"
            + f"\n\nUser constraints: water={profile.water_availability.value}, "
            f"budget_per_acre={profile.budget_per_acre:.0f}, "
            f"horizon={profile.horizon_months}mo, "
            f"risk_tolerance={profile.risk_tolerance.value}"
        )

        try:
            result = llm.complete(_CONFLICT_DETECTION_SYSTEM, user_prompt)
            return _ensure_dict(result)
        except Exception as e:
            logger.warning("Conflict detection failed: %s", e)
            return {"claims": [], "overall_confidence": 0.5}

    @staticmethod
    def _apply_adjustments(
        portfolio: list[CropPortfolioEntry],
        crop_ranking: list[CropScore],
        evidence: list[EvidenceCard],
    ) -> tuple[list[CropPortfolioEntry], list[str], list[str]]:
        """Apply rule-based adjustment policy on LLM findings.

        Policy (v1):
        - If any MAJOR_CONFLICT appears, propose and (if possible) swap out the
          *lowest-scoring* crop in the current portfolio with the best feasible backup.
        - If CONTEXT_DEPENDENT appears, keep the crop but add required actions.

        Note: We keep adjustments conservative and only swap using already-ranked
        feasible candidates.
        """
        warnings: list[str] = []
        actions: list[str] = []
        adjusted = list(portfolio)

        major_conflicts = [e for e in evidence if e.conflict_level == ConflictLevel.MAJOR_CONFLICT]
        context_deps = [e for e in evidence if e.conflict_level == ConflictLevel.CONTEXT_DEPENDENT]

        # Add context-dependent actions
        for cd in context_deps:
            if cd.snippet:
                actions.append(f"Condition: {cd.snippet}")

        if not major_conflicts:
            return adjusted, warnings, actions

        warnings.append(
            f"{len(major_conflicts)} major conflict(s) detected from web evidence. "
            "Attempting a conservative substitution using the next-best feasible crop."
        )

        # Pick the best feasible backup crop not already in the portfolio
        current_ids = {e.crop_id for e in adjusted}
        feasible_backup = [cs for cs in crop_ranking if not cs.eliminated and cs.crop_id not in current_ids]
        feasible_backup.sort(key=lambda cs: (-cs.final_score, cs.crop_id))

        if not feasible_backup:
            actions.append("No feasible backup crop found; keep current portfolio but review warnings.")
            return adjusted, warnings, actions

        backup = feasible_backup[0]

        # Swap out the lowest-score crop in current portfolio
        if adjusted:
            swap_idx = min(range(len(adjusted)), key=lambda i: adjusted[i].score)
            removed = adjusted[swap_idx]
            adjusted[swap_idx] = CropPortfolioEntry(
                crop_id=backup.crop_id,
                crop_name=backup.crop_name,
                area_fraction=removed.area_fraction,
                role_hint=removed.role_hint,
                score=backup.final_score,
            )
            actions.append(
                f"Substituted '{removed.crop_name}' → '{backup.crop_name}' due to major conflict evidence."
            )
        else:
            # Should not happen, but keep safe.
            adjusted = [
                CropPortfolioEntry(
                    crop_id=backup.crop_id,
                    crop_name=backup.crop_name,
                    area_fraction=1.0,
                    role_hint="PRIMARY",
                    score=backup.final_score,
                )
            ]
            actions.append(f"Selected fallback crop '{backup.crop_name}' due to major conflicts.")

        return adjusted, warnings, actions

    @staticmethod
    def _generate_grow_guide(
        llm: BaseLLMClient,
        profile: ValidatedProfile,
        practice: PracticeScore,
        entry: CropPortfolioEntry,
        user_context: str | None = None,
    ) -> GrowGuide:
        """Generate a structured grow guide via LLM."""
        user_prompt = (
            f"Generate a grow guide for:\n"
            f"- Crop: {entry.crop_name}\n"
            f"- Location: {profile.location}\n"
            f"- Practice: {practice.practice_name}\n"
            f"- Water availability: {profile.water_availability.value}\n"
            f"- Irrigation: {profile.irrigation_source.value}\n"
            f"- Time horizon: {profile.horizon_months} months\n"
        )
        if user_context and user_context.strip():
            user_prompt += f"- User context: {user_context.strip()}\n"
        user_prompt += "\nReturn as JSON with the specified keys."

        try:
            data = _ensure_dict(llm.complete(_GROW_GUIDE_SYSTEM, user_prompt))
            raw_timeline = data.get("monthly_timeline", ["Consult local calendar"])
            monthly_timeline = _normalize_monthly_timeline(
                raw_timeline if isinstance(raw_timeline, list) else [str(raw_timeline)]
            )
            return GrowGuide(
                crop_id=entry.crop_id,
                crop_name=entry.crop_name,
                sowing_window=data.get("sowing_window", "Consult local extension"),
                monthly_timeline=monthly_timeline,
                land_prep=data.get("land_prep", "Standard preparation"),
                irrigation_rules=data.get("irrigation_rules", "As per local practice"),
                fertilizer_plan=data.get("fertilizer_plan", "Balanced NPK"),
                pest_prevention=data.get("pest_prevention", ["Integrated pest management"]),
                harvest_notes=data.get("harvest_notes", "Harvest at maturity"),
                why_recommended=data.get("why_recommended", "Matches your constraints"),
                when_not_recommended=data.get("when_not_recommended", "When conditions differ significantly"),
            )
        except Exception as e:
            logger.warning("Grow guide generation failed for %s: %s", entry.crop_name, e)
            return GrowGuide(
                crop_id=entry.crop_id,
                crop_name=entry.crop_name,
                sowing_window="Consult local agricultural extension",
                monthly_timeline=["Consult local agricultural calendar"],
                land_prep="Standard land preparation for the region",
                irrigation_rules="Follow local irrigation practices",
                fertilizer_plan="Balanced NPK as per soil test",
                pest_prevention=["Integrated pest management recommended"],
                harvest_notes="Harvest at optimal maturity",
                why_recommended="Selected based on constraint matching",
                when_not_recommended="When local conditions differ significantly",
            )

    @staticmethod
    def _parse_conflict_level(level_str: str) -> ConflictLevel:
        try:
            return ConflictLevel(level_str)
        except ValueError:
            return ConflictLevel.NO_ISSUE

    @staticmethod
    def _compute_confidence(evidence: list[EvidenceCard]) -> float:
        """Heuristic confidence based on conflict distribution."""
        if not evidence:
            return 0.5

        severity = {
            ConflictLevel.NO_ISSUE: 1.0,
            ConflictLevel.MINOR_VARIATION: 0.85,
            ConflictLevel.CONTEXT_DEPENDENT: 0.6,
            ConflictLevel.MAJOR_CONFLICT: 0.2,
        }
        scores = [severity.get(e.conflict_level, 0.5) for e in evidence]
        return round(sum(scores) / len(scores), 2)
