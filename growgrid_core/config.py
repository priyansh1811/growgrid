"""GrowGrid AI configuration — env vars, constants, tuning parameters."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "growgrid.db"
CACHE_DIR = DATA_DIR / "cache"

# ── API keys ─────────────────────────────────────────────────────────────
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DATAGOV_API_KEY: str = os.getenv("DATAGOV_API_KEY", "579b464db66ec23bdd00000115faa24c1a404b076fc0a75eac4647fa")

# ── data.gov.in Mandi Price API ──────────────────────────────────────
DATAGOV_BASE_URL: str = "https://api.data.gov.in/resource"
DATAGOV_MANDI_RESOURCE_ID: str = "9ef84268-d588-465a-a308-a864a43d0070"

# ── CORS ─────────────────────────────────────────────────────────────────
# Comma-separated origins, e.g. "http://localhost:5173,https://app.example.com"
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()
]

# ── LLM settings ────────────────────────────────────────────────────────
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
LLM_TEMPERATURE: float = 0.2
LLM_MAX_TOKENS: int = 2048

# ── AHP constraint-tightening ────────────────────────────────────────────
ALPHA: float = 0.35  # tightening multiplier
GOAL_WEIGHT_MAX_MULTIPLIER: float = 1.5  # cap weight multiplier so one dimension doesn't dominate

# Goal classifier: time horizon tightness breakpoints (months)
GOAL_TIME_TIGHTNESS_MONTHS_TIER1: int = 6   # <= 6 mo → tightness 1.0
GOAL_TIME_TIGHTNESS_MONTHS_TIER2: int = 12  # <= 12 mo → 0.7
GOAL_TIME_TIGHTNESS_MONTHS_TIER3: int = 24  # <= 24 mo → 0.4; else 0.1

# ── Tavily cache ─────────────────────────────────────────────────────────
CACHE_TTL_HOURS: int = 168  # 7 days

# ── Practice scoring budget/feasibility thresholds ───────────────────────
POLYHOUSE_MIN_BUDGET_PER_ACRE: int = 50_000  # INR/acre (protected cultivation feasibility)
LOW_BUDGET_WARNING_THRESHOLD: int = 20_000  # INR/acre (warning threshold)
EXTREMELY_LOW_BUDGET_THRESHOLD: int = 10_000  # INR/acre (only minimal-input models likely)

# ── Feasibility thresholds ───────────────────────────────────────────────
ORCHARD_MIN_HORIZON_MONTHS: int = 24  # orchard-only needs patience
INTEGRATED_MIN_LAND_ACRES: float = 0.5  # typical minimum land for multi-component IFS

# ── Validation agent (warnings / UI) ─────────────────────────────────────
MICRO_PLOT_ACRES: float = 0.25  # land below this triggers micro-plot warning
HORIZON_EXTREME_WARNING_MONTHS: int = 3  # horizon below this: extreme short-horizon warning
HORIZON_SHORT_WARNING_MONTHS: int = 6  # horizon below this: short-horizon warning
LARGE_BUDGET_INR: int = 10_000_000  # budget above this: please-verify warning (1 crore)

# ── Practice recommender ─────────────────────────────────────────────────
PRACTICE_ALTERNATIVES_COUNT: int = 2  # number of alternative practices to return (after selected)

# ── Crop portfolio diversification thresholds ────────────────────────────
DIVERSIFY_LAND_THRESHOLD_2: float = 3.0  # acres → consider 2 crops
DIVERSIFY_LAND_THRESHOLD_3: float = 5.0  # acres → consider 3 crops
SCORE_GAP_FOR_70_30: float = 0.12

# ── Crop recommender LLM layer (explanation + user-context soft preferences) ─
# When True, uses LLM for portfolio explanation and to derive soft preferences from user_context.
# Requires OPENAI_API_KEY. Set to "false" to keep fully deterministic (e.g. tests).
CROP_LLM_LAYER_ENABLED: bool = os.getenv("CROP_LLM_LAYER_ENABLED", "true").lower() == "true"
