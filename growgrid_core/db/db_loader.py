"""Load CSV knowledge bases into SQLite for fast runtime queries."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from growgrid_core.config import DATA_DIR, DB_PATH

# ── Indexes (performance) ───────────────────────────────────────────────

_INDEX_DDL: list[str] = [
    # practice
    "CREATE INDEX IF NOT EXISTS idx_practice_master_code ON practice_master(practice_code)",
    "CREATE INDEX IF NOT EXISTS idx_practice_master_risk ON practice_master(risk_level)",
    "CREATE INDEX IF NOT EXISTS idx_practice_master_water ON practice_master(water_need)",
    "CREATE INDEX IF NOT EXISTS idx_practice_master_labour ON practice_master(labour_need)",
    "CREATE INDEX IF NOT EXISTS idx_practice_location_state ON practice_location_suitability(state)",
    "CREATE INDEX IF NOT EXISTS idx_practice_location_code ON practice_location_suitability(practice_code)",
    "CREATE INDEX IF NOT EXISTS idx_practice_irrigation_code ON practice_irrigation_suitability(practice_code)",
    "CREATE INDEX IF NOT EXISTS idx_practice_season_code ON practice_season_suitability(practice_code)",
    "CREATE INDEX IF NOT EXISTS idx_practice_season_season ON practice_season_suitability(season)",

    # crop
    "CREATE INDEX IF NOT EXISTS idx_crop_master_id ON crop_master(crop_id)",
    "CREATE INDEX IF NOT EXISTS idx_crop_master_water ON crop_master(water_need)",
    "CREATE INDEX IF NOT EXISTS idx_crop_master_labour ON crop_master(labour_need)",
    "CREATE INDEX IF NOT EXISTS idx_crop_master_risk ON crop_master(risk_level)",

    # compatibility join helpers
    "CREATE INDEX IF NOT EXISTS idx_cpc_practice ON crop_practice_compatibility(practice_code)",
    "CREATE INDEX IF NOT EXISTS idx_cpc_crop ON crop_practice_compatibility(crop_id)",
    "CREATE INDEX IF NOT EXISTS idx_cpc_practice_compat ON crop_practice_compatibility(practice_code, compatibility)",

    # crop location suitability
    "CREATE INDEX IF NOT EXISTS idx_cls_crop ON crop_location_suitability(crop_id)",
    "CREATE INDEX IF NOT EXISTS idx_cls_state ON crop_location_suitability(state)",

    # economics
    "CREATE INDEX IF NOT EXISTS idx_crop_cost_crop ON crop_cost_profile(crop_id)",
    "CREATE INDEX IF NOT EXISTS idx_yield_crop ON yield_baseline_bands(crop_id)",
    "CREATE INDEX IF NOT EXISTS idx_price_crop ON price_baseline_bands(crop_id)",
    "CREATE INDEX IF NOT EXISTS idx_scenario_ref_practice ON economics_scenario_reference(practice_code)",
    "CREATE INDEX IF NOT EXISTS idx_yield_state_crop ON yield_state_bands(crop_id)",
    "CREATE INDEX IF NOT EXISTS idx_yield_state_state ON yield_state_bands(state)",
    "CREATE INDEX IF NOT EXISTS idx_yield_state_crop_state ON yield_state_bands(crop_id, state)",
    "CREATE INDEX IF NOT EXISTS idx_irrigation_cost_source ON irrigation_cost_reference(irrigation_source)",
    "CREATE INDEX IF NOT EXISTS idx_fertilizer_input_name ON fertilizer_input_costs(input_name)",
    "CREATE INDEX IF NOT EXISTS idx_labour_share_category ON crop_labour_share(crop_category)",

    # spacing
    "CREATE INDEX IF NOT EXISTS idx_spacing_crop ON crop_spacing_reference(crop_id)",
    "CREATE INDEX IF NOT EXISTS idx_spacing_practice ON crop_spacing_reference(practice_code)",

    # schemes
    "CREATE INDEX IF NOT EXISTS idx_schemes_state ON schemes_metadata(state)",

    # ICAR
    "CREATE INDEX IF NOT EXISTS idx_icar_cc_state_season ON icar_crop_calendar(state, season)",
    "CREATE INDEX IF NOT EXISTS idx_icar_cc_crop ON icar_crop_calendar(crop_name)",
    "CREATE INDEX IF NOT EXISTS idx_icar_cc_state_season_crop ON icar_crop_calendar(state, season, crop_name)",
    "CREATE INDEX IF NOT EXISTS idx_icar_np_state_season ON icar_nutrient_plan(state, season)",
    "CREATE INDEX IF NOT EXISTS idx_icar_np_crop ON icar_nutrient_plan(crop_name)",
    "CREATE INDEX IF NOT EXISTS idx_icar_pd_state_season ON icar_pest_disease(state, season)",
    "CREATE INDEX IF NOT EXISTS idx_icar_pd_crop ON icar_pest_disease(crop_name)",
    "CREATE INDEX IF NOT EXISTS idx_icar_var_state_season ON icar_varieties(state, season)",
    "CREATE INDEX IF NOT EXISTS idx_icar_var_crop ON icar_varieties(crop_name)",
    "CREATE INDEX IF NOT EXISTS idx_icar_wm_state_season ON icar_weed_management(state, season)",
    "CREATE INDEX IF NOT EXISTS idx_icar_wm_crop ON icar_weed_management(crop_name)",
]


def create_indexes(conn: sqlite3.Connection) -> None:
    """Create performance indexes (idempotent)."""
    for ddl in _INDEX_DDL:
        conn.execute(ddl)
    conn.commit()

# ── DDL ──────────────────────────────────────────────────────────────────

_DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS practice_master (
        practice_code        TEXT PRIMARY KEY,
        practice_name        TEXT NOT NULL,
        water_need           TEXT NOT NULL,
        labour_need          TEXT NOT NULL,
        risk_level           TEXT NOT NULL,
        time_to_first_income_months_min INTEGER NOT NULL,
        time_to_first_income_months_max INTEGER NOT NULL,
        capex_min_per_acre_inr  INTEGER NOT NULL,
        capex_max_per_acre_inr  INTEGER NOT NULL,
        opex_min_per_acre_inr   INTEGER NOT NULL,
        opex_max_per_acre_inr   INTEGER NOT NULL,
        profit_potential     TEXT NOT NULL,
        perishability_exposure TEXT NOT NULL,
        storage_dependency   TEXT NOT NULL,
        suitable_when        TEXT,
        not_suitable_when    TEXT,
        source_id            TEXT,
        source_tier          TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS practice_infrastructure_requirement (
        practice_code    TEXT NOT NULL,
        requirement_code TEXT NOT NULL,
        requirement_level TEXT NOT NULL,
        PRIMARY KEY (practice_code, requirement_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS practice_location_suitability (
        practice_code TEXT NOT NULL,
        state         TEXT NOT NULL,
        suitability   TEXT NOT NULL,
        rationale     TEXT,
        PRIMARY KEY (practice_code, state)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS practice_irrigation_suitability (
        practice_code      TEXT NOT NULL,
        irrigation_source  TEXT NOT NULL,
        suitability        TEXT NOT NULL,
        rationale          TEXT,
        PRIMARY KEY (practice_code, irrigation_source)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS practice_season_suitability (
        practice_code TEXT NOT NULL,
        season        TEXT NOT NULL,
        suitability   TEXT NOT NULL,
        rationale     TEXT,
        PRIMARY KEY (practice_code, season)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS practice_cost_profile (
        practice_code TEXT NOT NULL,
        component     TEXT NOT NULL,
        cost_type     TEXT NOT NULL,
        min_inr_per_acre INTEGER,
        max_inr_per_acre INTEGER,
        notes         TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS practice_sources (
        source_id   TEXT PRIMARY KEY,
        source_name TEXT,
        source_type TEXT,
        url         TEXT,
        tier        TEXT,
        notes       TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS crop_master (
        crop_id          TEXT PRIMARY KEY,
        crop_name        TEXT NOT NULL,
        category         TEXT,
        seasons_supported TEXT,
        water_need       TEXT NOT NULL,
        labour_need      TEXT NOT NULL,
        risk_level       TEXT NOT NULL,
        time_to_first_income_months_min INTEGER NOT NULL,
        time_to_first_income_months_max INTEGER NOT NULL,
        profit_potential TEXT NOT NULL,
        perishability    TEXT,
        storage_need     TEXT,
        climate_tags     TEXT,
        notes            TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS crop_practice_compatibility (
        crop_id           TEXT NOT NULL,
        practice_code     TEXT NOT NULL,
        compatibility     TEXT NOT NULL,
        compatibility_score REAL NOT NULL,
        role_hint         TEXT,
        rationale         TEXT,
        PRIMARY KEY (crop_id, practice_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS crop_location_suitability (
        crop_id       TEXT NOT NULL,
        state         TEXT NOT NULL,
        suitability   TEXT NOT NULL,
        rationale     TEXT,
        source_tag    TEXT,
        PRIMARY KEY (crop_id, state)
    )
    """,
    # ── Economics tables ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS crop_cost_profile (
        crop_id          TEXT NOT NULL,
        component        TEXT NOT NULL,
        cost_type        TEXT NOT NULL,
        min_inr_per_acre INTEGER,
        max_inr_per_acre INTEGER,
        notes            TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS yield_baseline_bands (
        crop_id              TEXT PRIMARY KEY,
        low_yield_per_acre   REAL,
        base_yield_per_acre  REAL,
        high_yield_per_acre  REAL,
        yield_unit           TEXT,
        source_notes         TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_baseline_bands (
        crop_id              TEXT PRIMARY KEY,
        low_price_per_unit   REAL,
        base_price_per_unit  REAL,
        high_price_per_unit  REAL,
        price_unit           TEXT,
        source_notes         TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS loss_factor_reference (
        perishability_level TEXT PRIMARY KEY,
        loss_pct_low        REAL,
        loss_pct_base       REAL,
        loss_pct_high       REAL,
        notes               TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS economics_scenario_reference (
        practice_code                TEXT PRIMARY KEY,
        capital_buffer_floor_months  REAL,
        capex_contingency_pct        REAL,
        best_case_opex_multiplier    REAL,
        base_case_opex_multiplier    REAL,
        worst_case_opex_multiplier   REAL,
        notes                        TEXT
    )
    """,
    # ── State-specific yield bands table ─────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS yield_state_bands (
        crop_id              TEXT NOT NULL,
        state                TEXT NOT NULL,
        season               TEXT NOT NULL,
        low_yield_per_acre   REAL,
        base_yield_per_acre  REAL,
        high_yield_per_acre  REAL,
        data_points          INTEGER,
        PRIMARY KEY (crop_id, state, season)
    )
    """,
    # ── Irrigation cost reference table ───────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS irrigation_cost_reference (
        irrigation_source  TEXT PRIMARY KEY,
        capex_per_acre     REAL,
        opex_per_acre      REAL,
        notes              TEXT
    )
    """,
    # ── Fertilizer input costs table ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS fertilizer_input_costs (
        input_name      TEXT PRIMARY KEY,
        price_per_unit  REAL,
        unit            TEXT,
        subsidy_status  TEXT,
        notes           TEXT
    )
    """,
    # ── Crop labour share table ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS crop_labour_share (
        crop_category    TEXT PRIMARY KEY,
        labour_share_pct REAL,
        notes            TEXT
    )
    """,
    # ── Field layout table ──────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS crop_spacing_reference (
        crop_id          TEXT NOT NULL,
        practice_code    TEXT NOT NULL,
        row_spacing_cm   REAL,
        plant_spacing_cm REAL,
        plants_per_acre  INTEGER,
        planting_pattern TEXT,
        depth_cm         REAL,
        notes            TEXT,
        PRIMARY KEY (crop_id, practice_code)
    )
    """,
    # ── Government schemes table ────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schemes_metadata (
        scheme_id           TEXT PRIMARY KEY,
        scheme_name         TEXT NOT NULL,
        state               TEXT NOT NULL,
        ministry            TEXT,
        practice_tags       TEXT,
        crop_tags           TEXT,
        category_tags       TEXT,
        eligibility_summary TEXT,
        subsidy_pct         REAL,
        max_subsidy_inr     REAL,
        application_url     TEXT,
        source_url          TEXT,
        last_updated        TEXT,
        max_land_acres      REAL,
        farmer_type_tags    TEXT,
        gender_bonus_pct    REAL,
        season_window       TEXT,
        scheme_type         TEXT
    )
    """,
    # ── ICAR advisory tables ─────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS icar_crop_calendar (
        state              TEXT NOT NULL,
        season             TEXT NOT NULL,
        crop_name          TEXT NOT NULL,
        sub_region         TEXT,
        sow_start_month    INTEGER,
        sow_end_month      INTEGER,
        harvest_month_range TEXT,
        seed_rate_kg_ha    REAL,
        row_spacing_cm     REAL,
        plant_spacing_cm   REAL,
        nursery_days       INTEGER,
        duration_days      INTEGER,
        notes              TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS icar_nutrient_plan (
        state              TEXT NOT NULL,
        season             TEXT NOT NULL,
        crop_name          TEXT NOT NULL,
        sub_region         TEXT,
        N_kg_ha            REAL,
        P_kg_ha            REAL,
        K_kg_ha            REAL,
        FYM_t_ha           REAL,
        zinc_sulphate_kg_ha REAL,
        other_micronutrients TEXT,
        biofertilizers     TEXT,
        split_schedule     TEXT,
        application_notes  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS icar_pest_disease (
        state              TEXT NOT NULL,
        season             TEXT NOT NULL,
        crop_name          TEXT NOT NULL,
        sub_region         TEXT,
        pest_or_disease_name TEXT NOT NULL,
        type               TEXT,
        monitor_start_month INTEGER,
        monitor_end_month  INTEGER,
        chemical_control   TEXT,
        bio_control        TEXT,
        threshold_note     TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS icar_weed_management (
        state              TEXT NOT NULL,
        season             TEXT NOT NULL,
        crop_name          TEXT NOT NULL,
        sub_region         TEXT,
        pre_emergence_herbicide TEXT,
        pre_em_dose        TEXT,
        pre_em_timing_das  TEXT,
        post_emergence_herbicide TEXT,
        post_em_dose       TEXT,
        post_em_timing_das TEXT,
        manual_weeding_schedule TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS icar_varieties (
        state              TEXT NOT NULL,
        season             TEXT NOT NULL,
        crop_name          TEXT NOT NULL,
        sub_region         TEXT,
        variety_names      TEXT,
        variety_type       TEXT,
        duration_type      TEXT,
        purpose            TEXT
    )
    """,
]


# ── Public API ───────────────────────────────────────────────────────────


def _extract_table_name(ddl: str) -> str | None:
    """Extract table name from a CREATE TABLE statement."""
    import re
    m = re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)", ddl, re.IGNORECASE)
    return m.group(1) if m else None


def _expected_columns(ddl: str) -> set[str]:
    """Parse column names from a CREATE TABLE DDL statement."""
    import re
    # Match everything between the first '(' and last ')'
    m = re.search(r"\((.+)\)", ddl, re.DOTALL)
    if not m:
        return set()
    body = m.group(1)
    cols: set[str] = set()
    for line in body.split(","):
        token = line.strip().split()[0] if line.strip() else ""
        # Skip constraints / keywords
        if token and not token.upper().startswith(("PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT")):
            cols.add(token)
    return cols


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all tables. Drops and recreates if schema has changed."""
    for ddl in _DDL:
        table_name = _extract_table_name(ddl)
        if table_name:
            # Check if table exists with correct columns
            cur = conn.execute(f"PRAGMA table_info({table_name})")
            existing_cols = {row[1] for row in cur.fetchall()}
            if existing_cols:
                expected = _expected_columns(ddl)
                if expected and expected != existing_cols:
                    conn.execute(f"DROP TABLE {table_name}")
        conn.execute(ddl)
    conn.commit()


def _load_csv_into_table(
    conn: sqlite3.Connection,
    csv_path: Path,
    table_name: str,
) -> int:
    """Read a CSV and load into an existing table.

    Important: We **do not** use `if_exists="replace"` because it drops the
    table (and with it: PKs, constraints, and indexes). Instead we clear the
    table and append.
    """
    if not csv_path.exists():
        return 0

    try:
        df = pd.read_csv(csv_path)
    except pd.errors.ParserError:
        # Fallback: Python engine skips or warns on bad lines (e.g. extra commas in notes)
        df = pd.read_csv(csv_path, engine="python", on_bad_lines="skip")

    # Basic cleanup: ensure NaNs become NULLs (not the string 'nan')
    df = df.where(pd.notnull(df), None)

    # Clear existing rows but keep schema
    conn.execute(f"DELETE FROM {table_name}")
    conn.commit()

    # Append rows
    df.to_sql(table_name, conn, if_exists="append", index=False)
    return len(df)


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection to the existing DB file. Safe to call from any thread.

    Use this in request handlers; do not share one connection across threads.
    Assumes the DB has already been populated (e.g. via load_all() at startup).
    """
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _load_icar_tables(conn: sqlite3.Connection, data_dir: Path) -> None:
    """Load ICAR advisory CSVs from kharif/ and rabi/ subdirs, deduplicated.

    Each season directory contains: icar_crop_calendar.csv, icar_nutrient_plan.csv,
    icar_pest_disease.csv, icar_weed_management.csv, icar_varieties.csv.
    We concatenate both seasons and drop exact-duplicate rows before loading.
    """
    icar_tables = [
        "icar_crop_calendar",
        "icar_nutrient_plan",
        "icar_pest_disease",
        "icar_weed_management",
        "icar_varieties",
    ]
    icar_dirs = [data_dir / "icar" / "kharif", data_dir / "icar" / "rabi"]

    for table_name in icar_tables:
        csv_name = f"{table_name}.csv"
        frames: list[pd.DataFrame] = []

        for icar_dir in icar_dirs:
            csv_path = icar_dir / csv_name
            if not csv_path.exists():
                continue
            try:
                df = pd.read_csv(csv_path)
            except pd.errors.ParserError:
                df = pd.read_csv(csv_path, engine="python", on_bad_lines="skip")
            frames.append(df)

        if not frames:
            continue

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.drop_duplicates()
        # Drop rows where any NOT NULL column is missing
        cur = conn.execute(f"PRAGMA table_info({table_name})")
        not_null_cols = [row[1] for row in cur.fetchall() if row[3]]  # col[3] = notnull flag
        nn_present = [c for c in not_null_cols if c in combined.columns]
        if nn_present:
            combined = combined.dropna(subset=nn_present)
        combined = combined.where(pd.notnull(combined), None)

        # Clear existing rows and append fresh
        conn.execute(f"DELETE FROM {table_name}")
        conn.commit()
        combined.to_sql(table_name, conn, if_exists="append", index=False)


def load_all(db_path: Path | None = None, data_dir: Path | None = None) -> sqlite3.Connection:
    """Load every CSV into the SQLite database. Returns the connection."""
    db_path = db_path or DB_PATH
    data_dir = data_dir or DATA_DIR

    conn = get_connection(db_path)

    create_tables(conn)

    csv_table_map: dict[str, str] = {
        "practice_master.csv": "practice_master",
        "practice_infrastructure_requirement.csv": "practice_infrastructure_requirement",
        "practice_location_suitability.csv": "practice_location_suitability",
        "practice_irrigation_suitability.csv": "practice_irrigation_suitability",
        "practice_season_suitability.csv": "practice_season_suitability",
        "practice_cost_profile.csv": "practice_cost_profile",
        "practice_sources.csv": "practice_sources",
        "crop_master.csv": "crop_master",
        "crop_practice_compatibility.csv": "crop_practice_compatibility",
        "crop_location_suitability.csv": "crop_location_suitability",
        # Economics
        "crop_cost_profile.csv": "crop_cost_profile",
        "yield_baseline_bands.csv": "yield_baseline_bands",
        "price_baseline_bands.csv": "price_baseline_bands",
        "loss_factor_reference.csv": "loss_factor_reference",
        "economics_scenario_reference.csv": "economics_scenario_reference",
        "yield_state_bands.csv": "yield_state_bands",
        "irrigation_cost_reference.csv": "irrigation_cost_reference",
        "fertilizer_input_costs.csv": "fertilizer_input_costs",
        "crop_labour_share.csv": "crop_labour_share",
        # Field layout
        "crop_spacing_reference.csv": "crop_spacing_reference",
        # Government schemes
        "schemes_metadata.csv": "schemes_metadata",
    }

    for csv_name, table_name in csv_table_map.items():
        _load_csv_into_table(conn, data_dir / csv_name, table_name)

    # ── Load ICAR advisory CSVs (kharif + rabi, deduplicated) ────────
    _load_icar_tables(conn, data_dir)

    # Create indexes after data load (idempotent)
    create_indexes(conn)

    # Optional: update SQLite planner statistics
    try:
        conn.execute("ANALYZE")
    except sqlite3.OperationalError:
        pass

    return conn
