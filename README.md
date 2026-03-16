# GrowGrid AI

Explainable decision-support pipeline for farming planning in India.

## What it does

1. Collects 9 structured inputs (location, land, water, budget, goal, etc.)
2. Validates inputs and derives constraints
3. Converts user goal into a weight vector (AHP-based)
4. Selects the best **farming practice** using deterministic DB rules + scoring
5. Recommends a **crop portfolio** (1-3 crops) with area split
6. Verifies recommendations via **Agronomist Expert** (LLM + Tavily web search)
7. Generates a short **grow guide** per crop

## Design Principles

- DB + hard filters are the primary decision engine
- LLM + Tavily is a verification/advisory layer, never the primary recommender
- All scoring is deterministic and explainable

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your TAVILY_API_KEY and OPENAI_API_KEY

# Initialize database from CSVs
python -c "from growgrid_core.db.db_loader import load_all; load_all()"

# Run the API and web UI
uvicorn apps.api.main:app --reload --port 8000   # API
cd apps/web && npm install && npm run dev        # Web dashboard at http://localhost:5173
```

## Run Tests

```bash
pytest tests/ -v
```

## Project Structure

```
apps/                  - REST API (FastAPI) + Web dashboard (React)
growgrid_core/
  agents/              - Pipeline agents (validation, goal, practice, crop, agronomist)
  db/                  - Database loader and queries
  services/            - Pipeline orchestrator
  tools/               - External API clients (Tavily, LLM, cache)
  utils/               - Enums, Pydantic types, scoring functions
data/                  - CSV knowledge bases + SQLite DB
tests/                 - Unit and integration tests
```
