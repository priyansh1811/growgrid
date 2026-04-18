#!/usr/bin/env python3
"""
ICAR Rabi Agro Advisory PDF Extraction Pipeline
- 31 states detected (Goa absent from this Rabi advisory)
- Pages 25-436 = English advisories; 437-755 = regional language (skipped)
- Appends to existing kharif tables in growgrid.db (if_exists="append")
- Uses OpenAI gpt-4.1-mini with OPENAI_API_KEY from .env
"""

import os, json, csv, time, re, sqlite3
from pathlib import Path
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
from collections import defaultdict

load_dotenv()

# ── CONFIG ──────────────────────────────────────────────────────────────────
PDF_PATH   = Path("/Users/priyansh18/Downloads/Rabi-Agro-Advisory-2021-22.pdf")
BASE_DIR   = Path("/Users/priyansh18/Downloads/growgrid3-main")
OUTPUT_DIR = BASE_DIR / "data/icar/rabi"
CHUNKS_DIR = OUTPUT_DIR / "chunks"
DB_PATH    = BASE_DIR / "data/growgrid.db"
PROGRESS_F = OUTPUT_DIR / ".progress.json"
ERRORS_LOG = OUTPUT_DIR / "errors.log"
SEASON     = "rabi"
MAX_CHARS  = 18000
MAX_TOKENS = 8000
MODEL      = "gpt-4.1-mini"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

# ── CONFIRMED STATE PAGE RANGES (0-indexed) ──────────────────────────────────
# Auto-detected by scanning PDF headers. Goa is absent from this Rabi advisory.
# Pages 437-755 are regional language versions — not processed.
STATE_RANGES = [
    {"state": "Himachal Pradesh",            "start": 24,  "end": 35},
    {"state": "Punjab",                       "start": 35,  "end": 54},
    {"state": "Jammu and Kashmir",            "start": 54,  "end": 77},
    {"state": "Ladakh",                       "start": 77,  "end": 83},
    {"state": "Uttarakhand",                  "start": 83,  "end": 93},
    {"state": "Rajasthan",                    "start": 93,  "end": 125},
    {"state": "Haryana and Delhi",            "start": 125, "end": 138},
    {"state": "Uttar Pradesh",               "start": 138, "end": 181},
    {"state": "Bihar",                        "start": 181, "end": 198},
    {"state": "Jharkhand",                    "start": 198, "end": 214},
    {"state": "West Bengal",                  "start": 214, "end": 223},
    {"state": "Odisha",                       "start": 223, "end": 233},
    {"state": "Andaman and Nicobar Islands",  "start": 233, "end": 242},
    {"state": "Assam",                        "start": 242, "end": 249},
    {"state": "Sikkim",                       "start": 249, "end": 255},
    {"state": "Arunachal Pradesh",            "start": 255, "end": 266},
    {"state": "Manipur",                      "start": 266, "end": 277},
    {"state": "Meghalaya",                    "start": 277, "end": 287},
    {"state": "Mizoram",                      "start": 287, "end": 299},
    {"state": "Nagaland",                     "start": 299, "end": 305},
    {"state": "Tripura",                      "start": 305, "end": 314},
    {"state": "Maharashtra",                  "start": 314, "end": 325},
    {"state": "Gujarat",                      "start": 325, "end": 330},
    {"state": "Madhya Pradesh",               "start": 330, "end": 341},
    {"state": "Chhattisgarh",                 "start": 341, "end": 357},
    {"state": "Andhra Pradesh",               "start": 357, "end": 374},
    {"state": "Telangana",                    "start": 374, "end": 387},
    {"state": "Tamil Nadu and Puducherry",    "start": 387, "end": 403},
    {"state": "Karnataka",                    "start": 403, "end": 421},
    {"state": "Kerala",                       "start": 421, "end": 432},
    {"state": "Lakshadweep",                  "start": 432, "end": 436},
]

TABLES = ["crop_calendar", "nutrient_plan", "pest_disease", "weed_management", "varieties"]

FIELDNAMES = {
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
                       "pre_em_dose","pre_em_timing_das","post_emergence_herbicide","post_em_dose",
                       "post_em_timing_das","manual_weeding_schedule"],
    "varieties":      ["state","season","crop_name","sub_region","variety_names","variety_type",
                       "duration_type","purpose"],
}

EXTRACTION_PROMPT = """You are a precise agricultural data extractor. Extract ALL structured data from this ICAR {season} season advisory for {state}.
Return ONLY a single valid JSON object with exactly these 5 keys. No markdown fences, no explanation, no prose — just raw JSON.

Rules:
- Extract EVERY crop mentioned: cereals, pulses, oilseeds, vegetables, fruits, spices, plantation crops, commercial crops, fodder crops
- Months as integers: January=1, February=2, March=3, April=4, May=5, June=6, July=7, August=8, September=9, October=10, November=11, December=12
- All measurements as numbers only, no units in the value: "120 kg/ha" → 120, "45 cm" → 45, "2.5 t/ha" → 2.5
- Missing or unmentioned fields → null
- States with sub-regions (North Gujarat, Western Maharashtra, Marathwada, Vidarbha, Konkan, hills, plains, etc.) → fill sub_region field
- variety_type values: "hybrid" or "HYV" or "variety" or null
- duration_type values: "early" or "medium" or "late" or "short" or "long" or null
- pest_disease type values: "pest" or "disease" only
- NPK shorthand "N:P:K = 120:60:40 kg/ha" → N_kg_ha=120, P_kg_ha=60, K_kg_ha=40
- split_schedule: plain English description e.g. "half basal at sowing, half top-dress at 30 DAS"
- Create one pest_disease row per pest or disease per crop — do not combine multiple pests into one row
- Create one varieties row per crop per duration group — if early/medium/late varieties are listed separately, make separate rows
- For weed_management, if only manual weeding is mentioned with no herbicides, still create a row with null herbicide fields and fill manual_weeding_schedule
- Rabi crops include: wheat, barley, mustard, linseed, gram/chickpea, lentil, pea, potato, onion, garlic, sunflower, safflower, coriander, cumin, fenugreek, spinach, radish, carrot, turnip, cabbage, cauliflower, broccoli, tomato (rabi), maize (rabi), sorghum (rabi), boro rice

{{
  "crop_calendar": [
    {{
      "state": "{state}",
      "season": "{season}",
      "crop_name": "",
      "sub_region": null,
      "sow_start_month": null,
      "sow_end_month": null,
      "harvest_month_range": null,
      "seed_rate_kg_ha": null,
      "row_spacing_cm": null,
      "plant_spacing_cm": null,
      "nursery_days": null,
      "duration_days": null,
      "notes": null
    }}
  ],
  "nutrient_plan": [
    {{
      "state": "{state}",
      "season": "{season}",
      "crop_name": "",
      "sub_region": null,
      "N_kg_ha": null,
      "P_kg_ha": null,
      "K_kg_ha": null,
      "FYM_t_ha": null,
      "zinc_sulphate_kg_ha": null,
      "other_micronutrients": null,
      "biofertilizers": null,
      "split_schedule": null,
      "application_notes": null
    }}
  ],
  "pest_disease": [
    {{
      "state": "{state}",
      "season": "{season}",
      "crop_name": "",
      "sub_region": null,
      "pest_or_disease_name": "",
      "type": "",
      "monitor_start_month": null,
      "monitor_end_month": null,
      "chemical_control": null,
      "bio_control": null,
      "threshold_note": null
    }}
  ],
  "weed_management": [
    {{
      "state": "{state}",
      "season": "{season}",
      "crop_name": "",
      "sub_region": null,
      "pre_emergence_herbicide": null,
      "pre_em_dose": null,
      "pre_em_timing_das": null,
      "post_emergence_herbicide": null,
      "post_em_dose": null,
      "post_em_timing_das": null,
      "manual_weeding_schedule": null
    }}
  ],
  "varieties": [
    {{
      "state": "{state}",
      "season": "{season}",
      "crop_name": "",
      "sub_region": null,
      "variety_names": "",
      "variety_type": null,
      "duration_type": null,
      "purpose": null
    }}
  ]
}}

TEXT FROM {state} (RABI SEASON):
{text}"""


# ── HELPERS ──────────────────────────────────────────────────────────────────

def safe_name(state: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', state.lower()).strip('_')


def load_progress() -> set:
    if PROGRESS_F.exists():
        return set(json.loads(PROGRESS_F.read_text()))
    return set()


def save_progress(done: set):
    PROGRESS_F.write_text(json.dumps(sorted(done), indent=2))


def append_to_csv(table: str, rows: list):
    csv_path = OUTPUT_DIR / f"icar_{table}.csv"
    file_exists = csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES[table], extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def log_error(state: str, msg: str):
    with open(ERRORS_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {state} | {msg}\n")


# ── EXTRACT TEXT CHUNK ────────────────────────────────────────────────────────

def extract_chunk(pdf, state_range: dict) -> str:
    state = state_range["state"]
    sname = safe_name(state)
    chunk_path = CHUNKS_DIR / f"{sname}.txt"

    if chunk_path.exists():
        text = chunk_path.read_text(encoding="utf-8")
        print(f"  [cached chunk] {len(text):,} chars")
        return text

    pages_text = []
    for p_idx in range(state_range["start"], state_range["end"] + 1):
        try:
            t = pdf.pages[p_idx].extract_text() or ""
            pages_text.append(t)
        except Exception as e:
            pages_text.append(f"[PAGE ERROR: {e}]")

    full_text = "\n".join(pages_text)
    chunk_path.write_text(full_text, encoding="utf-8")
    return full_text


# ── OPENAI API CALL ───────────────────────────────────────────────────────────

def call_llm(client: OpenAI, state: str, text: str) -> dict | None:
    truncated = text[:MAX_CHARS]
    prompt = EXTRACTION_PROMPT.format(
        state=state,
        season=SEASON,
        text=truncated
    )

    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a precise agricultural data extractor. Always return valid JSON only."},
                    {"role": "user",   "content": prompt}
                ]
            )
            raw = response.choices[0].message.content or ""
            cleaned = strip_fences(raw)
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError as e:
            print(f"    ⚠ JSON parse error (attempt {attempt}/3): {e}")
            if attempt == 1:
                (OUTPUT_DIR / f"_bad_{safe_name(state)}.txt").write_text(raw)
            if attempt < 3:
                time.sleep(5)
        except Exception as e:
            err_str = str(e)
            if "rate" in err_str.lower() or "429" in err_str:
                print(f"    ⚠ Rate limit (attempt {attempt}/3), sleeping 30s...")
                time.sleep(30)
            else:
                print(f"    ⚠ API error (attempt {attempt}/3): {e}")
                if attempt < 3:
                    time.sleep(5)

    return None


# ── SQLITE LOAD ───────────────────────────────────────────────────────────────

def load_to_sqlite():
    print("\n=== PHASE: Loading CSVs into growgrid.db (append mode) ===")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    for table in TABLES:
        csv_path = OUTPUT_DIR / f"icar_{table}.csv"
        if not csv_path.exists():
            print(f"  SKIP icar_{table} (no CSV found)")
            continue
        df = pd.read_csv(csv_path)
        rabi_df = df[df["season"] == "rabi"] if "season" in df.columns else df
        rabi_df.to_sql(f"icar_{table}", conn, if_exists="append", index=False)
        print(f"  icar_{table}: {len(rabi_df):,} rabi rows appended")

    # Show total counts
    print("\n  === Total rows per table (all seasons) ===")
    for table in TABLES:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM icar_{table}").fetchone()[0]
            by_season = conn.execute(
                f"SELECT season, COUNT(*) FROM icar_{table} GROUP BY season"
            ).fetchall()
            breakdown = ", ".join(f"{s}: {c}" for s, c in by_season)
            print(f"  icar_{table}: {count:,} total ({breakdown})")
        except Exception as e:
            print(f"  icar_{table}: {e}")

    conn.close()
    print(f"\n  DB path: {DB_PATH}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("ICAR RABI ADVISORY 2021-22 — FULL EXTRACTION PIPELINE")
    print(f"PDF: {PDF_PATH}")
    print(f"States: {len(STATE_RANGES)} | Season: {SEASON}")
    print("=" * 70)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("[ERROR] OPENAI_API_KEY not set — check your .env file")
    client = OpenAI(api_key=api_key)
    done = load_progress()

    if done:
        print(f"\nResuming — {len(done)} states already done: {sorted(done)}")

    # Save manifest
    manifest = {
        "pdf": str(PDF_PATH),
        "season": SEASON,
        "total_states": len(STATE_RANGES),
        "note": "Goa absent from this Rabi advisory. Pages 437-755 are regional language versions.",
        "ranges": STATE_RANGES
    }
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))

    total_counts = defaultdict(int)
    failed_states = []

    print(f"\n=== EXTRACTING {len(STATE_RANGES)} STATES ===\n")

    with pdfplumber.open(PDF_PATH) as pdf:
        print(f"PDF opened: {len(pdf.pages)} pages total\n")

        for i, sr in enumerate(STATE_RANGES, 1):
            state = sr["state"]
            pages_n = sr["end"] - sr["start"] + 1

            if state in done:
                print(f"[{i:2d}/{len(STATE_RANGES)}] ✓ SKIP {state}")
                continue

            print(f"[{i:2d}/{len(STATE_RANGES)}] → {state} (pages {sr['start']+1}–{sr['end']+1}, {pages_n} pages)")

            # Extract text
            text = extract_chunk(pdf, sr)
            char_count = len(text)
            print(f"  Text: {char_count:,} chars → truncating to {min(char_count, MAX_CHARS):,}")

            if char_count < 100:
                print(f"  ⚠ Very short text — skipping (likely image-only pages)")
                log_error(state, f"Text too short: {char_count} chars")
                failed_states.append(state)
                continue

            # Call OpenAI API
            data = call_llm(client, state, text)

            if data is None:
                log_error(state, "Failed after 3 retries")
                print(f"  ✗ FAILED — logged to errors.log")
                failed_states.append(state)
                continue

            # Write CSVs
            counts = {}
            for table in TABLES:
                rows = data.get(table, [])
                if not isinstance(rows, list):
                    rows = []
                if rows:
                    append_to_csv(table, rows)
                counts[table] = len(rows)
                total_counts[table] += len(rows)

            summary = " | ".join(f"{t}: {counts[t]}" for t in TABLES)
            print(f"  ✓ {state} → {summary}")

            done.add(state)
            save_progress(done)
            time.sleep(1)

    # ── FINAL SUMMARY ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"\n{'Table':<30} {'Rabi rows':>12}")
    print("-" * 45)
    grand_total = 0
    for table in TABLES:
        csv_path = OUTPUT_DIR / f"icar_{table}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            n = len(df)
            grand_total += n
            print(f"  icar_{table:<26} {n:>10,}")
        else:
            print(f"  icar_{table:<26} {'(no file)':>10}")
    print("-" * 45)
    print(f"  {'TOTAL':<28} {grand_total:>10,}")

    if failed_states:
        print(f"\n⚠ Failed states ({len(failed_states)}): {failed_states}")
        print(f"  See: {ERRORS_LOG}")

    print(f"\n  Chunks: {CHUNKS_DIR}")
    print(f"  CSVs:   {OUTPUT_DIR}")

    # Load to SQLite
    load_to_sqlite()

    print("\n🎉 Pipeline complete!")
    print(f"   CSVs → {OUTPUT_DIR}")
    print(f"   DB   → {DB_PATH}")


if __name__ == "__main__":
    main()
