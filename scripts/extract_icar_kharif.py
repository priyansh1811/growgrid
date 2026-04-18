"""
Extract structured agricultural data from ICAR Kharif 2025 PDF → CSVs + SQLite.
Uses OpenAI gpt-4.1-mini with OPENAI_API_KEY from .env.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import time
from pathlib import Path

import pypdf
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PDF_PATH = Path("/Users/priyansh18/Downloads/ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf")
OUT_DIR   = Path("data/icar/kharif")
CHUNKS    = OUT_DIR / "chunks"
PROGRESS  = OUT_DIR / ".progress.json"
ERRLOG    = OUT_DIR / "errors.log"
DB_PATH   = Path("data/growgrid.db")

MODEL      = "gpt-4.1-mini"
MAX_TOKENS = 8000
TEXT_LIMIT = 14000
RETRIES    = 3
DELAY      = 5

TABLES = ["crop_calendar", "nutrient_plan", "pest_disease", "weed_management", "varieties"]

HEADERS: dict[str, list[str]] = {
    "crop_calendar":  ["state","season","crop_name","sub_region","sow_start_month","sow_end_month",
                        "harvest_month_range","seed_rate_kg_ha","row_spacing_cm","plant_spacing_cm",
                        "nursery_days","duration_days","notes"],
    "nutrient_plan":  ["state","season","crop_name","sub_region","N_kg_ha","P_kg_ha","K_kg_ha",
                        "FYM_t_ha","zinc_sulphate_kg_ha","other_micronutrients","biofertilizers",
                        "split_schedule","application_notes"],
    "pest_disease":   ["state","season","crop_name","sub_region","pest_or_disease_name","type",
                        "monitor_start_month","monitor_end_month","chemical_control","bio_control",
                        "threshold_note"],
    "weed_management":["state","season","crop_name","sub_region","pre_emergence_herbicide",
                        "pre_em_dose","pre_em_timing_das","post_emergence_herbicide",
                        "post_em_dose","post_em_timing_das","manual_weeding_schedule"],
    "varieties":      ["state","season","crop_name","sub_region","variety_names","variety_type",
                        "duration_type","purpose"],
}

STATES: list[tuple[str, int, int]] = [
    ("Andaman and Nicobar Islands", 1, 4),
    ("Andhra Pradesh", 5, 18),
    ("Arunachal Pradesh", 19, 23),
    ("Assam", 24, 31),
    ("Bihar", 32, 38),
    ("Chhattisgarh", 39, 45),
    ("Goa", 46, 48),
    ("Gujarat", 49, 60),
    ("Haryana and Delhi", 61, 67),
    ("Himachal Pradesh", 68, 82),
    ("Jammu and Kashmir", 83, 103),
    ("Jharkhand", 104, 109),
    ("Karnataka", 110, 119),
    ("Kerala", 120, 124),
    ("Ladakh", 125, 130),
    ("Lakshadweep", 131, 132),
    ("Madhya Pradesh", 133, 138),
    ("Maharashtra", 139, 161),
    ("Manipur", 162, 167),
    ("Meghalaya", 168, 171),
    ("Mizoram", 172, 177),
    ("Nagaland", 178, 186),
    ("Odisha", 187, 190),
    ("Punjab", 191, 208),
    ("Rajasthan", 209, 232),
    ("Sikkim", 233, 236),
    ("Tamil Nadu and Puducherry", 237, 242),
    ("Telangana", 243, 249),
    ("Tripura", 250, 252),
    ("Uttar Pradesh", 253, 263),
    ("Uttarakhand", 264, 279),
    ("West Bengal", 280, 292),
]

PROMPT = """\
You are a precise agricultural data extractor. Extract ALL structured data from this ICAR {season} season advisory for {state}.

Return ONLY a single valid JSON object with exactly these 5 keys. No markdown fences, no explanation — just raw JSON.

Rules:
- Extract EVERY crop mentioned: cereals, pulses, oilseeds, vegetables, fruits, spices, plantation crops, commercial crops
- Months as integers: Jan=1 … Dec=12
- Measurements as numbers only (no units): "120 kg/ha" → 120, "45 cm" → 45, "2.5 t/ha" → 2.5
- Missing fields → null
- Sub-regions (North Gujarat, Marathwada, Vidarbha, Konkan, etc.) → fill sub_region
- variety_type: "hybrid" | "HYV" | "variety" | null
- duration_type: "early" | "medium" | "late" | "short" | "long" | null
- pest_disease type: "pest" | "disease" only
- NPK "N:P:K = 120:60:40 kg/ha" → N_kg_ha=120, P_kg_ha=60, K_kg_ha=40
- split_schedule: plain English, e.g. "half basal at sowing, half top-dress at 30 DAS"
- One pest_disease row per pest/disease per crop
- One varieties row per crop per duration group
- Weed management with only manual weeding: row with null herbicide fields, fill manual_weeding_schedule

{{
  "crop_calendar": [
    {{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,
      "sow_start_month":null,"sow_end_month":null,"harvest_month_range":null,
      "seed_rate_kg_ha":null,"row_spacing_cm":null,"plant_spacing_cm":null,
      "nursery_days":null,"duration_days":null,"notes":null}}
  ],
  "nutrient_plan": [
    {{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,
      "N_kg_ha":null,"P_kg_ha":null,"K_kg_ha":null,"FYM_t_ha":null,
      "zinc_sulphate_kg_ha":null,"other_micronutrients":null,"biofertilizers":null,
      "split_schedule":null,"application_notes":null}}
  ],
  "pest_disease": [
    {{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,
      "pest_or_disease_name":"","type":"","monitor_start_month":null,"monitor_end_month":null,
      "chemical_control":null,"bio_control":null,"threshold_note":null}}
  ],
  "weed_management": [
    {{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,
      "pre_emergence_herbicide":null,"pre_em_dose":null,"pre_em_timing_das":null,
      "post_emergence_herbicide":null,"post_em_dose":null,"post_em_timing_das":null,
      "manual_weeding_schedule":null}}
  ],
  "varieties": [
    {{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,
      "variety_names":"","variety_type":null,"duration_type":null,"purpose":null}}
  ]
}}

TEXT FROM {state} (KHARIF SEASON):
{text}"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def safe(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def detect_offset(reader: pypdf.PdfReader) -> int:
    for i in range(9, 25):
        t = reader.pages[i].extract_text() or ""
        if "Andaman" in t and t.strip().startswith("1"):
            log.info("Andaman at PDF page %d → offset=%d", i + 1, i)
            return i
    log.warning("Offset not found, using default 15")
    return 15


def state_text(reader: pypdf.PdfReader, doc_start: int, doc_end: int, offset: int) -> str:
    start = doc_start - 1 + offset
    end   = min(doc_end - 1 + offset + 1, len(reader.pages) - 1)
    parts, prev = [], None
    for i in range(start, end + 1):
        t = reader.pages[i].extract_text() or ""
        if t and t != prev:
            parts.append(t)
            prev = t
    return "\n\n".join(parts)


def strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def call_llm(client: OpenAI, state: str, text: str) -> dict:
    prompt = PROMPT.format(state=state, season="kharif", text=text[:TEXT_LIMIT])
    for attempt in range(1, RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a precise agricultural data extractor. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = resp.choices[0].message.content or "{}"
            return json.loads(strip_fences(raw))
        except Exception as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, RETRIES, state, exc)
            if attempt < RETRIES:
                time.sleep(DELAY)
    raise RuntimeError(f"All retries failed for {state}")


def append_csv(table: str, rows: list[dict]) -> None:
    path = OUT_DIR / f"icar_{table}.csv"
    new  = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS[table], extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def load_progress() -> set[str]:
    return set(json.loads(PROGRESS.read_text())) if PROGRESS.exists() else set()


def save_progress(done: set[str]) -> None:
    PROGRESS.write_text(json.dumps(sorted(done), indent=2))


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("[ERROR] OPENAI_API_KEY not set in .env")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS.mkdir(parents=True, exist_ok=True)

    reader = pypdf.PdfReader(str(PDF_PATH))
    log.info("PDF: %d pages", len(reader.pages))
    offset = detect_offset(reader)

    client   = OpenAI(api_key=api_key)
    done     = load_progress()
    manifest: dict[str, int] = {}

    # ── Step 1: save text chunks ──────────────────────────────────────────
    log.info("Saving text chunks …")
    for state, s, e in STATES:
        cf = CHUNKS / f"{safe(state)}.txt"
        if cf.exists():
            text = cf.read_text(encoding="utf-8")
        else:
            text = state_text(reader, s, e, offset)
            cf.write_text(text, encoding="utf-8")
        manifest[state] = len(text)

    (CHUNKS / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ── Step 2: LLM extraction → CSV ─────────────────────────────────────
    log.info("Starting LLM extraction for %d states …", len(STATES))
    for state, _, __ in STATES:
        if state in done:
            log.info("Skip %s (done)", state)
            continue

        text = (CHUNKS / f"{safe(state)}.txt").read_text(encoding="utf-8")

        try:
            data = call_llm(client, state, text)
        except RuntimeError as exc:
            log.error("%s", exc)
            with open(ERRLOG, "a") as f:
                f.write(f"{state}: {exc}\n")
            continue

        counts: dict[str, int] = {}
        for tbl in TABLES:
            rows = data.get(tbl, [])
            if rows:
                append_csv(tbl, rows)
            counts[tbl] = len(rows) if rows else 0

        done.add(state)
        save_progress(done)
        print(f"{state} → " + " | ".join(f"{t}: {counts[t]}" for t in TABLES))

    # ── Step 3: Summary ───────────────────────────────────────────────────
    print("\n=== CSV Summary ===")
    for tbl in TABLES:
        p = OUT_DIR / f"icar_{tbl}.csv"
        n = sum(1 for _ in open(p, encoding="utf-8")) - 1 if p.exists() else 0
        print(f"  icar_{tbl}.csv : {n} rows")

    # ── Step 4: SQLite load ───────────────────────────────────────────────
    import pandas as pd, sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    for tbl in TABLES:
        p = OUT_DIR / f"icar_{tbl}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        df.to_sql(f"icar_{tbl}", conn, if_exists="replace", index=False)
        print(f"icar_{tbl}: {len(df)} rows → growgrid.db")
    conn.close()
    print("\nAll done.")


if __name__ == "__main__":
    main()
