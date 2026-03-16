# GrowGrid AI — Cursor Context (Build Guide, Step-by-Step)
Scope (current implementation): Practice Selection + Crop Recommendation + Agronomist Verification + short grow guide.
Future agents (listed below) will be added later: Economist, Govt Schemes RAG, Field Layout, Critic, Report Composer, Email.
ML yield/price models are out of scope for now.

---

## 1) What GrowGrid AI does (in this phase)
GrowGrid AI is an explainable decision-support pipeline for farming planning. It:
1) Collects 9 structured inputs from a Streamlit form.
2) Validates inputs + derives constraints.
3) Converts the user goal into a weight vector (AHP-based template + constraint-tightening).
4) Selects the most suitable **type of farming practice** using deterministic DB rules + scoring.
5) Recommends a **crop portfolio** (1–3 crops) using deterministic DB + compatibility matrix + scoring.
6) Runs an **Agronomist Expert Verifier** that uses LLM reasoning + web search (Tavily) only to:
   - double-check suitability,
   - detect conflicts,
   - suggest safe adjustments,
   - then generate a short “how to grow” guide per final crop.
7) (Engineering improvement) Uses **caching** for Tavily results to reduce repeated searches and stabilize outputs.

Key design principle:
- DB + hard filters are the primary decision engine.
- LLM + Tavily is a verification/advisory layer, never the primary recommender.

---

## 2) UI Inputs (Streamlit Form)
Collect these 9 inputs (store as PlanRequest JSON):
1) `location` (State + District as string)
2) `land_area_acres` (float)
3) `water_availability` ∈ {LOW, MED, HIGH}
4) `irrigation_source` ∈ {NONE, CANAL, BOREWELL, DRIP, MIXED}
5) `budget_total_inr` (int)
6) `labour_availability` ∈ {LOW, MED, HIGH}
7) `goal` ∈ {MAXIMIZE_PROFIT, STABLE_INCOME, WATER_SAVING, FAST_ROI}
8) `time_horizon_years` (float)
9) `risk_tolerance` ∈ {LOW, MED, HIGH}

Derived features (computed after validation):
- `budget_per_acre = budget_total_inr / land_area_acres`
- `horizon_months = round(time_horizon_years * 12)`

Optional later (not now):
- market_access, soil_type

---

## 3) High-level pipeline (agent sequence)
Single entrypoint:
`run_pipeline(plan_request_json) -> plan_response_json`

### Recommended order (full roadmap)
Phase-0 (current):
1) Validation & Sanity Checker
2) Goal Classifier (AHP template + constraint tightening)
3) Type of Farming Recommender (Practice Selection)
4) Crop Recommender (Crop Portfolio)
5) Agronomist Expert Verifier (LLM + Tavily + final grow guide)

Phase-1/Next (later):
6) Economist Agent (Cost + Profitability/ROI + Sensitivity)
7) Govt Schemes Agent (RAG)
8) Field Layout Planner Agent
9) Critic / Consistency Agent
10) Report Composer Agent
11) Email Delivery Agent

Pipeline state is a dict updated at each step.

---

## 4) Databases (deterministic knowledge layer)

### 4.1 Practice Knowledge DB (Type of Farming Recommender)
Primary tables / CSVs:
1) `practice_master`
   - `practice_code` (unique)
   - `practice_name`
   - `water_need` (LOW/MED/HIGH)
   - `labour_need` (LOW/MED/HIGH)
   - `risk_level` (LOW/MED/HIGH)
   - `time_to_first_income_months_min/max`
   - `capex_min_per_acre_inr`, `capex_max_per_acre_inr`
   - `opex_min_per_acre_inr`, `opex_max_per_acre_inr`
   - `profit_potential` (LOW/MED/HIGH/VERY_HIGH)
   - `perishability_exposure` (LOW/MED/HIGH)
   - `storage_dependency` (LOW/MED/HIGH)
   - `suitable_when` (text)
   - `not_suitable_when` (text)
   - `source_id`, `source_tier`
2) `practice_infrastructure_requirement`
   - `practice_code`
   - `requirement_code`
   - `requirement_level` (REQUIRED/RECOMMENDED/OPTIONAL)
3) `practice_cost_profile`
   - `practice_code`
   - component-wise CAPEX/OPEX ranges
4) `practice_sources`
   - authoritative source registry

Storage:
- Maintain CSVs under `data/` for editing.
- Build SQLite for runtime queries (optional but recommended for clean joins).

### 4.2 Crop Knowledge DB (Crop Recommender)
Primary tables / CSVs:
1) `crop_master`
   - `crop_id` (unique)
   - `crop_name`
   - `category`
   - `seasons_supported` standardized tokens:
     - PERENNIAL / YEAR_ROUND / "KHARIF,RABI,ZAID"
   - `water_need` (LOW/MED/HIGH)
   - `labour_need` (LOW/MED/HIGH)
   - `risk_level` (LOW/MED/HIGH)
   - `time_to_first_income_months_min/max`
   - `profit_potential` (LOW/MED/HIGH)
   - `perishability` (LOW/MED/HIGH)
   - `storage_need` (YES/NO)
   - `climate_tags` (comma-separated tags)
   - `notes` (text)
2) `crop_practice_compatibility`  ✅ crucial
   - `crop_id`
   - `practice_code`
   - `compatibility` (GOOD/MED/POOR)
   - `compatibility_score` (1.0 / 0.6 / 0.2)
   - `role_hint` (PRIMARY/INTERCROP/NA)
   - `rationale` (text)
3) Optional now, useful later:
   - `crop_spacing_open_field`
   - `crop_spacing_orchard`

### 4.3 Agronomy Knowledge (for Agronomist Agent)
(Phase-0 can be lightweight; Phase-1 can be richer)
- `crop_agronomy_calendar` (crop_id, region_tag, sowing_start, sowing_end, harvest_start, harvest_end)
- `crop_irrigation_guidelines` (crop_id, stage, frequency, notes)
- `crop_nutrient_plan` (crop_id, stage, NPK ranges, micronutrients)
- `pest_disease_risks` (crop_id, pests, diseases, preventive_steps)

### 4.4 Economics Knowledge (for Economist Agent) — later
- `input_cost_reference` (seed, fert, pesticide, mulch, drip parts, etc.)
- `labour_rate_reference` (region-wise)
- `crop_cost_profile` (crop_id, capex/opex components)
- `yield_baseline_bands` (crop_id, low/base/high yield per acre)
- `price_baseline_bands` (crop_id, low/base/high farmgate price)
- `loss_factor_reference` (perishability-based %)

### 4.5 Schemes Knowledge (for Govt Schemes RAG) — later
- scheme docs + vector index (PDFs, official pages, guidelines)
- metadata table (scheme_name, state, crop/practice tags, eligibility tags)

---

## 5) Agent 1 — Validation & Sanity Checker
Purpose:
- enforce correct enums + types
- compute derived fields
- produce hard and soft constraints
- produce warnings and recommended fixes

### Inputs
PlanRequest

### Outputs (write into state)
- `validated_profile` (normalized + derived)
- `hard_constraints` (list of rules)
- `soft_constraints` (list of preferences/penalties)
- `warnings` (list of strings)

### Example hard-constraint rules
- land_area_acres > 0
- budget_total_inr > 0
- horizon_months > 0
- if water_availability=LOW: later drop water_need=HIGH practices/crops
- if budget_per_acre is below certain threshold: later drop protected cultivation

No LLM here. Deterministic.

---

## 6) Agent 2 — Goal Classifier (AHP-based + constraint-tightening)
Purpose:
Convert user goal into weight vector W across these dimensions:
`profit, risk, water, labour, time, capex`

### 6.1 Base weight templates (AHP-derived)
Use fixed templates (already derived offline via AHP) for each goal.

Example template set:
- MAXIMIZE_PROFIT: profit 0.431, risk 0.151, water 0.139, labour 0.097, time 0.092, capex 0.092
- STABLE_INCOME:   profit 0.085, risk 0.418, water 0.184, labour 0.098, time 0.112, capex 0.103
- WATER_SAVING:    profit 0.058, risk 0.190, water 0.426, labour 0.090, time 0.094, capex 0.142
- FAST_ROI:        profit 0.225, risk 0.086, water 0.086, labour 0.053, time 0.403, capex 0.146

### 6.2 Constraint-tightening (weight adjustment)
Compute tightness for each dimension (0..1):
- water_tightness: LOW=1.0, MED=0.5, HIGH=0.0
- labour_tightness: LOW=1.0, MED=0.5, HIGH=0.0
- time_tightness: horizon_months short => higher tightness
- capex_tightness: budget_per_acre low => higher tightness (simple budget bands)
- risk_tightness: risk_tolerance LOW => higher
- profit_tightness: optional (generally 0)

Adjust weights:
`w' = normalize( w * (1 + alpha * tightness) )`
alpha ~ 0.35

Output:
- final weight vector `W`
- an explanation string describing changes (for UI transparency)

---

## 7) Agent 3 — Type of Farming Recommender (Practice Selection)
Purpose:
Choose the best farming model using PracticeDB and weights.

### Step 7.1 Fetch all practices
From DB: active practices.

### Step 7.2 HARD FILTERS (elimination gate)
Drop infeasible practices:
- Water: if user water LOW → drop practice water_need HIGH
- Budget: if capex_min_per_acre > budget_per_acre → drop
- Labour: if user labour LOW → drop labour_need HIGH
- Horizon: if horizon_months < 24 → drop orchard-only (keep orchard+intercrop)

Return feasible candidates (2–5 typical).

### Step 7.3 Compute fit scores (0..1) per practice
Compute:
- water_fit
- labour_fit
- capex_fit
- time_fit
- risk_fit
- profit_fit

Mappings:
Ordinal match (LOW/MED/HIGH):
- perfect match => 1.0
- one-step mismatch => 0.6
- opposite => 0.2

capex_fit:
- if budget >= capex_max => 1.0
- if capex_min <= budget < capex_max => 0.6 + 0.4 * (budget-min)/(max-min)
- if budget < capex_min => 0.0 (filtered)

time_fit:
- if horizon >= time_max => 1.0
- if time_min <= horizon < time_max => 0.6 + 0.4 * (horizon-time_min)/(time_max-time_min)
- if horizon < time_min => 0.0 (filtered)

risk_fit example:
- risk_tol LOW: LOW=1.0, MED=0.6, HIGH=0.2
- risk_tol MED: LOW=0.8, MED=1.0, HIGH=0.5
- risk_tol HIGH: LOW=0.6, MED=0.8, HIGH=1.0

profit_fit map:
LOW=0.3, MED=0.6, HIGH=0.85, VERY_HIGH=0.95

### Step 7.4 Final practice score (weighted sum)
`Score(practice) = Σ (w_dim * fit_dim)`

Return:
- top practice
- top-2 alternatives
- score breakdown table per practice
- elimination reasons for dropped practices

---

## 8) Agent 4 — Crop Recommender (Crop Portfolio)
Purpose:
Given selected practice, recommend crops + optional area split.

### Step 8.1 Candidate fetch by compatibility
Get crops where compatibility is GOOD or MED for selected practice.

### Step 8.2 HARD FILTERS
- water LOW → drop crops with water_need HIGH
- labour LOW → drop crops with labour_need HIGH
- horizon_months < crop time_to_first_income_min → drop
- risk_tol LOW → drop risk_level HIGH (or apply heavy penalty; prefer drop for safety)

### Step 8.3 Crop fit scoring (0..1)
Compute same dimensions where available:
- profit_fit, risk_fit, water_fit, labour_fit, time_fit
- capex_fit optional until crop_cost_profile exists (can omit for now)

### Step 8.4 Compatibility multiplier
FinalCropScore:
`Final = (Σ w_dim * fit_dim) * compatibility_score`

### Step 8.5 Portfolio selection logic
Default:
- choose Top-1 crop
Diversification:
- if land_area_acres large OR risk_tol LOW → choose Top-2 or Top-3

Area split:
- if score1 - score2 >= 0.12 → 70/30
- else → 60/40
- for 3 crops → 50/30/20

Return:
- ranked list + score breakdown
- selected portfolio + split
- reasons + rejected reasons

---

## 9) Agent 5 — Agronomist Expert (Verifier + Short Grow Guide)
Purpose:
This agent does NOT choose from scratch.
It verifies the current recommendation using LLM reasoning + Tavily/web search, suggests safe corrections, then outputs a short grow guide.
Also includes a short seasonal timeline (Kharif/Rabi/Zaid-style month plan) inside the guide.

### Phase 9.1 Build claims to verify
Convert plan into checkable claims:
- "Practice X is feasible for budget/water/labour constraints"
- "Crop Y is suitable in location Z in current season(s)"
- "Crop Y water requirement aligns with user water availability"
- "Time to first income aligns with horizon"
- "Major risks are manageable given user risk tolerance"

### Phase 9.2 Tavily search (targeted)
For each crop and practice:
- generate 2–4 precise queries including location + crop + season
- fetch top 3–5 results per query

### Phase 9.3 Evidence extraction
Extract only:
- sowing/planting window
- climate/temp suitability notes
- irrigation intensity notes
- major pests/diseases
- time to harvest / first income
- hard warnings ("not recommended if...")

Store as Evidence Cards with URLs.

### Phase 9.4 Conflict detection
Classify evidence vs DB + current selection:
- NO_ISSUE
- MINOR_VARIATION
- CONTEXT_DEPENDENT
- MAJOR_CONFLICT

### Phase 9.5 Rule-based adjustment policy (important)
- Hard constraints always win.
- If MAJOR_CONFLICT affects hard constraints → propose change:
  - swap crop with next-best feasible from ranked list
  - or downgrade it to optional + add warning
- If CONTEXT_DEPENDENT → keep crop but add required conditions (drip, resistant variety, market access, etc.)
- If MINOR_VARIATION → keep crop; refine guidance text.

Outputs:
- verified_practice (same or adjusted)
- verified_crop_portfolio (same or adjusted)
- confidence_score (0..1)
- warnings + required_actions
- citations list (urls)

### Phase 9.6 Short grow guide generation (+ short seasonal timeline)
For each final crop:
- sowing/planting window (location/season aligned)
- short month-wise timeline (e.g., Month 1: sowing/transplant, Month 2–3: veg stage, Month 3–4: harvest)
- land prep + sowing/transplant method
- irrigation thumb rules by stage
- fertilizer plan (simple NPK stages)
- top 3 pest/disease prevention points
- harvesting & post-harvest notes
Also:
- 1 line: why recommended
- 1 line: when NOT recommended

---

## 9.7 Tavily Cache (engineering requirement)
To avoid repeated searches and make outputs stable, cache Tavily results.

### Cache key (recommendation)
Use a deterministic key like:
- `cache_key = f"{location}|{practice_code}|{crop_id}|{season_token}|v1"`

### Cache policy
- If key exists and is fresh → reuse stored results.
- If not → call Tavily, store results, then proceed.
Implementation options:
- Simple JSON file cache under `data/cache/`
- SQLite table `tool_cache(cache_key TEXT PRIMARY KEY, payload_json TEXT, created_at TEXT)`

---

## 10) Future Agents (roadmap; NOT implemented now)

### 10.1 Economist Agent (Cost + Profitability/ROI + Sensitivity) — later
Purpose:
- Compute CAPEX/OPEX per acre and total (itemized)
- Compute revenue/profit ranges, break-even, ROI bands
- Add sensitivity analysis (simple stress tests)

Inputs:
- selected practice, crop portfolio + area split
- budget_per_acre, labour availability, irrigation source
- yield/price baseline bands (from DB)

Outputs:
- `cost_breakdown` (capex/opex per crop + totals)
- `roi_summary` (best/base/worst)
- `breakeven_months`, `roi_percent_range`
- `sensitivity` (price -15%, yield -10%, labour +10%)

### 10.2 Govt Schemes Agent (RAG) — later
Purpose:
- Retrieve relevant schemes based on:
  - user location/state
  - selected practice (drip/polyhouse/orchard)
  - crop tags (horticulture, vegetables, etc.)
- Provide citations and eligibility checklist

Inputs:
- user profile + selected practice/crops
- scheme KB/vector index

Outputs:
- ranked schemes + citations
- eligibility checklist
- documents list + application steps (high-level)

### 10.3 Field Layout Planner Agent — later
Purpose:
- Convert crop portfolio + area split into:
  - spacing plan
  - plant count/tree count
  - block-level layout suggestions
- Produce layout JSON that can be plotted later.

Inputs:
- selected crops, area split, spacing tables

Outputs:
- `layout_plan` JSON
- `plant_counts`
- `spacing_used`

### 10.4 Critic / Consistency Agent — later
Purpose:
- Red-team the complete plan and catch contradictions:
  - water LOW but high-water crop
  - budget mismatch
  - horizon mismatch
  - missing steps for perishable crops
- Suggest fixes (prefer minimal edits).

Inputs:
- full plan state

Outputs:
- `issues[]`, `fixes[]`, `final_confidence`

### 10.5 Report Composer Agent — later
Purpose:
- Assemble all outputs into a structured report payload:
  - executive summary
  - chosen practice + reasoning
  - crops + area split + grow guides
  - economics tables
  - schemes section
  - layout section
  - risks & mitigations
- Produce PDF-ready sections later.

Outputs:
- `report_payload` (JSON)
- `pdf_sections` (structured)

### 10.6 Email Delivery Agent — later
Purpose:
- Send report PDF/link to user and store delivery status.

Outputs:
- `email_status` (sent/failed), timestamp, retries

---

## 11) Output JSON (PlanResponse)
Return a single structured JSON for UI display (Phase-0):
- validated_profile
- constraints + warnings
- goal_weights W + explanation
- practice_ranking (top N with breakdown)
- selected_practice + alternatives
- crop_ranking (top N with breakdown)
- selected_crop_portfolio + split
- agronomist_verification (confidence, warnings, actions, citations)
- grow_guides (per crop)

(Phase-1 later adds:)
- economics (cost + ROI)
- schemes
- layout
- critic_report
- report_payload + email_status

---

## 12) Suggested Code Layout
repo/
  apps/
    streamlit_app.py
  growgrid_core/
    services/
      plan_runner.py
    agents/
      validation_agent.py
      goal_classifier_agent.py
      practice_recommender_agent.py
      crop_recommender_agent.py
      agronomist_verifier_agent.py
      economist_agent.py (later)
      govt_schemes_agent.py (later)
      field_layout_agent.py (later)
      critic_agent.py (later)
      report_composer_agent.py (later)
      email_delivery_agent.py (later)
    db/
      db_loader.py
      queries.py
    utils/
      enums.py
      scoring.py
      types.py   # Pydantic models
    tools/
      tavily_client.py
      tool_cache.py
  data/
    practice_master.csv
    practice_infrastructure_requirement.csv
    practice_cost_profile.csv
    practice_sources.csv
    crop_master.csv
    crop_practice_compatibility.csv
    crop_spacing_open_field.csv (optional)
    cache/ (optional if file-based caching)
  tests/
    test_validation.py
    test_practice_scoring.py
    test_crop_scoring.py
    test_tavily_cache.py (optional)

---

## 13) Guardrails (to keep project defendable)
- Recommendation is DB-driven + deterministic (filters + scoring).
- LLM is used only for verification + guidance.
- Any LLM-suggested change must be:
  - consistent with hard constraints,
  - taken from already-feasible ranked candidates,
  - explained with evidence.

END.