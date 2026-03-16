# GrowGrid Apps

## REST API (FastAPI)

The API exposes the GrowGrid pipeline over HTTP. Used by the web dashboard.

**Run from project root:**

```bash
# From repo root (growgrid cursor/)
pip install -r requirements.txt
uvicorn apps.api.main:app --reload --port 8000
```

- **Base URL:** `http://127.0.0.1:8000`
- **Docs:** `http://127.0.0.1:8000/docs`

**Endpoints:**

- `GET /api/health` — health check
- `POST /api/clarify` — body: `FormInputs` → `ClarificationResult`
- `POST /api/refine` — body: `{ form_inputs, answers }` → `RefinementResult`
- `POST /api/plan` — body: `PlanRequest` → `PlanResponse`
- `POST /api/plan-from-form` — body: `{ form_inputs, refinement? }` → `PlanResponse`

## Web dashboard (React + Vite)

Professional UI that calls the API.

**Run from project root:**

```bash
cd apps/web
npm install
npm run dev
```

- **App:** `http://localhost:5173`
- Vite proxies `/api` to `http://127.0.0.1:8000`, so run the API first.

**Flow:** Farm form → (optional) clarification questions → Submit/Skip → Plan results (practice, crops, verification, grow guides).
