#!/usr/bin/env python3
"""
Retry failed Rabi states with increased max_tokens and reduced input chars.
Fixes truncated JSON by giving the model more output budget.
"""

import os, json, csv, time, re, sqlite3
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
from collections import defaultdict

load_dotenv()

BASE_DIR   = Path("/Users/priyansh18/Downloads/growgrid3-main")
OUTPUT_DIR = BASE_DIR / "data/icar/rabi"
CHUNKS_DIR = OUTPUT_DIR / "chunks"
DB_PATH    = BASE_DIR / "data/growgrid.db"
PROGRESS_F = OUTPUT_DIR / ".progress.json"
ERRORS_LOG = OUTPUT_DIR / "errors.log"
SEASON     = "rabi"
MAX_CHARS  = 12000   # Reduced input → more room for output
MAX_TOKENS = 16000   # Doubled → fits full JSON response
MODEL      = "gpt-4.1-mini"

FAILED_STATES = [
    {"state": "Himachal Pradesh",         "start": 24,  "end": 35},
    {"state": "Jammu and Kashmir",        "start": 54,  "end": 77},
    {"state": "Odisha",                   "start": 223, "end": 233},
    {"state": "Andhra Pradesh",           "start": 357, "end": 374},
    {"state": "Tamil Nadu and Puducherry","start": 387, "end": 403},
    {"state": "Karnataka",               "start": 403, "end": 421},
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
- Months as integers: January=1 ... December=12
- All measurements as numbers only (no units): "120 kg/ha" → 120
- Missing fields → null
- Sub-regions → fill sub_region field
- variety_type: "hybrid" or "HYV" or "variety" or null
- duration_type: "early" or "medium" or "late" or "short" or "long" or null
- pest_disease type: "pest" or "disease" only
- NPK: "N:P:K = 120:60:40" → N_kg_ha=120, P_kg_ha=60, K_kg_ha=40
- One row per pest/disease per crop; one row per variety group per crop
- Rabi crops include: wheat, barley, mustard, linseed, chickpea/gram, lentil, pea, potato, onion, garlic, sunflower, safflower, coriander, cumin, fenugreek, spinach, radish, carrot, turnip, cabbage, cauliflower, tomato (rabi), maize (rabi), boro rice

{{
  "crop_calendar": [{{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,"sow_start_month":null,"sow_end_month":null,"harvest_month_range":null,"seed_rate_kg_ha":null,"row_spacing_cm":null,"plant_spacing_cm":null,"nursery_days":null,"duration_days":null,"notes":null}}],
  "nutrient_plan": [{{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,"N_kg_ha":null,"P_kg_ha":null,"K_kg_ha":null,"FYM_t_ha":null,"zinc_sulphate_kg_ha":null,"other_micronutrients":null,"biofertilizers":null,"split_schedule":null,"application_notes":null}}],
  "pest_disease": [{{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,"pest_or_disease_name":"","type":"","monitor_start_month":null,"monitor_end_month":null,"chemical_control":null,"bio_control":null,"threshold_note":null}}],
  "weed_management": [{{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,"pre_emergence_herbicide":null,"pre_em_dose":null,"pre_em_timing_das":null,"post_emergence_herbicide":null,"post_em_dose":null,"post_em_timing_das":null,"manual_weeding_schedule":null}}],
  "varieties": [{{"state":"{state}","season":"{season}","crop_name":"","sub_region":null,"variety_names":"","variety_type":null,"duration_type":null,"purpose":null}}]
}}

TEXT FROM {state} (RABI SEASON):
{text}"""


def safe_name(s): return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

def strip_fences(t):
    t = t.strip()
    t = re.sub(r'^```(?:json)?\s*', '', t)
    t = re.sub(r'\s*```$', '', t)
    return t.strip()

def append_to_csv(table, rows):
    csv_path = OUTPUT_DIR / f"icar_{table}.csv"
    exists = csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES[table], extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerows(rows)

def load_progress():
    if PROGRESS_F.exists():
        return set(json.loads(PROGRESS_F.read_text()))
    return set()

def save_progress(done):
    PROGRESS_F.write_text(json.dumps(sorted(done), indent=2))

def call_llm(client, state, text):
    truncated = text[:MAX_CHARS]
    prompt = EXTRACTION_PROMPT.format(state=state, season=SEASON, text=truncated)

    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a precise agricultural data extractor. Return valid complete JSON only."},
                    {"role": "user",   "content": prompt}
                ]
            )
            raw = response.choices[0].message.content or ""
            data = json.loads(strip_fences(raw))
            return data
        except json.JSONDecodeError as e:
            print(f"    ⚠ JSON error (attempt {attempt}/3): {e}")
            if attempt == 1:
                (OUTPUT_DIR / f"_bad_{safe_name(state)}.txt").write_text(raw)
            if attempt < 3: time.sleep(5)
        except Exception as e:
            err = str(e)
            wait = 30 if "rate" in err.lower() or "429" in err else 5
            print(f"    ⚠ Error (attempt {attempt}/3): {e}")
            if attempt < 3: time.sleep(wait)
    return None


def main():
    print("=" * 60)
    print("RABI RETRY — 6 failed states (16k token budget)")
    print("=" * 60)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("[ERROR] OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)
    done = load_progress()

    import pdfplumber
    PDF_PATH = Path("/Users/priyansh18/Downloads/Rabi-Agro-Advisory-2021-22.pdf")

    with pdfplumber.open(PDF_PATH) as pdf:
        for i, sr in enumerate(FAILED_STATES, 1):
            state = sr["state"]
            if state in done:
                print(f"[{i}/6] ✓ SKIP {state} (already done)")
                continue

            print(f"\n[{i}/6] → {state} (pages {sr['start']+1}–{sr['end']+1})")

            # Load from cached chunk
            chunk_path = CHUNKS_DIR / f"{safe_name(state)}.txt"
            if chunk_path.exists():
                text = chunk_path.read_text(encoding="utf-8")
            else:
                pages_text = []
                for p_idx in range(sr["start"], sr["end"] + 1):
                    try: pages_text.append(pdf.pages[p_idx].extract_text() or "")
                    except: pages_text.append("")
                text = "\n".join(pages_text)
                chunk_path.write_text(text)

            print(f"  Text: {len(text):,} chars → truncating to {min(len(text), MAX_CHARS):,}")

            data = call_llm(client, state, text)
            if data is None:
                print(f"  ✗ FAILED again — skipping")
                with open(ERRORS_LOG, "a") as f:
                    f.write(f"RETRY FAILED: {state}\n")
                continue

            counts = {}
            for table in TABLES:
                rows = data.get(table, [])
                if not isinstance(rows, list): rows = []
                if rows: append_to_csv(table, rows)
                counts[table] = len(rows)

            summary = " | ".join(f"{t}: {counts[t]}" for t in TABLES)
            print(f"  ✓ {state} → {summary}")
            done.add(state)
            save_progress(done)
            time.sleep(1)

    # Final summary
    print("\n" + "=" * 60)
    print("RETRY COMPLETE — Final CSV totals")
    print("=" * 60)
    grand = 0
    for t in TABLES:
        p = OUTPUT_DIR / f"icar_{t}.csv"
        if p.exists():
            df = pd.read_csv(p)
            n = len(df)
            grand += n
            print(f"  icar_{t}: {n:,} rows")
    print(f"  TOTAL: {grand:,} rows")

    # Reload all rabi data into DB
    print("\nReloading rabi data into growgrid.db...")
    conn = sqlite3.connect(DB_PATH)

    # First remove existing rabi rows, then re-append fresh
    for t in TABLES:
        p = OUTPUT_DIR / f"icar_{t}.csv"
        if not p.exists(): continue
        df = pd.read_csv(p)
        rabi_df = df[df["season"] == "rabi"] if "season" in df.columns else df

        # Delete old rabi rows from this table
        try:
            conn.execute(f"DELETE FROM icar_{t} WHERE season = 'rabi'")
            conn.commit()
        except Exception:
            pass

        # Append fresh rabi rows
        rabi_df.to_sql(f"icar_{t}", conn, if_exists="append", index=False)
        total = conn.execute(f"SELECT COUNT(*) FROM icar_{t}").fetchone()[0]
        print(f"  icar_{t}: {len(rabi_df):,} rabi rows → {total:,} total in DB")

    conn.close()
    print(f"\n✅ Done. DB: {DB_PATH}")


if __name__ == "__main__":
    main()
