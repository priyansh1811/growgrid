"""
GrowGrid REST API — clarification and plan pipeline.

Run from project root:
  uvicorn apps.api.main:app --reload --port 8000

CORS is enabled via ALLOWED_ORIGINS env. DB and Tavily cache are initialized once at startup.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from growgrid_core.agents.step_0_clarification_agent import (
    ClarificationAgent,
    ClarificationResult,
    RefinementResult,
)
from growgrid_core.config import ALLOWED_ORIGINS
from growgrid_core.db.db_loader import get_connection, load_all
from growgrid_core.services.plan_runner import run_pipeline
from growgrid_core.tools.tool_cache import ToolCache
from growgrid_core.utils.enums import Goal, IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import PlanRequest, PlanResponse, PlanValidationError

# Populate DB once at startup (main thread); then each request gets its own connection.
_load_db_once = load_all()
_load_db_once.close()

_CACHE = ToolCache()

app = FastAPI(
    title="GrowGrid API",
    description="Clarification and plan generation for smart farming recommendations",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/response schemas for API (mirror frontend needs) ──────────────


class FormInputs(BaseModel):
    """Form payload for clarify and refine."""

    name: str = Field(default="")
    email: str = Field(default="")
    category: str = Field(default="general")
    location: str = Field(..., min_length=1)
    land_area_acres: float = Field(..., gt=0)
    water_availability: str  # WaterLevel value
    irrigation_source: str
    budget_total_inr: int = Field(..., gt=0)
    labour_availability: str
    goal: str  # Goal value
    time_horizon_years: float = Field(..., gt=0)
    risk_tolerance: str  # RiskLevel value
    planning_month: int | None = Field(default=None, ge=1, le=12)  # 1–12 for season-aware recommendations

    @field_validator("planning_month", mode="before")
    @classmethod
    def coerce_planning_month(cls, v: object) -> int | None:
        if v is None or v == "":
            return None
        if isinstance(v, int):
            return v if 1 <= v <= 12 else None
        try:
            m = int(v)
            return m if 1 <= m <= 12 else None
        except (TypeError, ValueError):
            return None


class ClarifyAnswer(BaseModel):
    question_id: str
    answer: str


class RefineBody(BaseModel):
    form_inputs: FormInputs
    answers: list[ClarifyAnswer] = Field(default_factory=list)


def _form_to_dict(f: FormInputs) -> dict[str, Any]:
    return f.model_dump()


def _build_plan_request(form_dict: dict[str, Any], refinement: RefinementResult) -> PlanRequest:
    """Build PlanRequest from form dict and optional refinement overrides."""
    goal = refinement.suggested_goal or form_dict["goal"]
    risk = refinement.suggested_risk_tolerance or form_dict["risk_tolerance"]
    planning_month = form_dict.get("planning_month")
    if planning_month is not None and planning_month != "":
        try:
            m = int(planning_month)
            planning_month = m if 1 <= m <= 12 else None
        except (TypeError, ValueError):
            planning_month = None
    else:
        planning_month = None
    return PlanRequest(
        name=form_dict.get("name") or None,
        email=form_dict.get("email") or None,
        location=form_dict["location"],
        land_area_acres=float(form_dict["land_area_acres"]),
        water_availability=WaterLevel(form_dict["water_availability"]),
        irrigation_source=IrrigationSource(form_dict["irrigation_source"]),
        budget_total_inr=int(form_dict["budget_total_inr"]),
        labour_availability=LabourLevel(form_dict["labour_availability"]),
        goal=Goal(goal),
        time_horizon_years=float(form_dict["time_horizon_years"]),
        risk_tolerance=RiskLevel(risk),
        user_context=refinement.user_context,
        planning_month=planning_month,
    )


# ── Endpoints ───────────────────────────────────────────────────────────────


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/clarify", response_model=ClarificationResult)
def clarify(form: FormInputs) -> ClarificationResult:
    """Analyse form inputs and return whether follow-up questions are needed."""
    try:
        agent = ClarificationAgent()
        return agent.analyze(_form_to_dict(form))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refine", response_model=RefinementResult)
def refine(body: RefineBody) -> RefinementResult:
    """Refine goal/risk from form + clarification answers."""
    try:
        agent = ClarificationAgent()
        form_dict = _form_to_dict(body.form_inputs)
        answers = [{"question_id": a.question_id, "answer": a.answer} for a in body.answers]
        return agent.refine(form_dict, answers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plan", response_model=PlanResponse)
def plan(request: PlanRequest) -> PlanResponse:
    """Run the full pipeline and return the plan response."""
    conn = get_connection()
    try:
        return run_pipeline(request, conn=conn, cache=_CACHE)
    except PlanValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


class PlanFromFormBody(BaseModel):
    form_inputs: FormInputs
    refinement: RefinementResult | None = None


@app.post("/api/plan-from-form", response_model=PlanResponse)
def plan_from_form(body: PlanFromFormBody) -> PlanResponse:
    """Build PlanRequest from form + optional refinement (e.g. after clarify), then run pipeline."""
    ref = body.refinement or RefinementResult()
    conn = get_connection()
    try:
        req = _build_plan_request(_form_to_dict(body.form_inputs), ref)
        return run_pipeline(req, conn=conn, cache=_CACHE)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except PlanValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ── Static file serving (production) ──────────────────────────────────────

_STATIC_DIR = ROOT / "apps" / "web" / "dist"
if _STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        """Serve the React SPA for any non-API route."""
        file_path = _STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_STATIC_DIR / "index.html")
