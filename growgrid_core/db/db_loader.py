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
]


# ── Public API ───────────────────────────────────────────────────────────


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all tables (idempotent via IF NOT EXISTS)."""
    for ddl in _DDL:
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

    df = pd.read_csv(csv_path)

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


def load_all(db_path: Path | None = None, data_dir: Path | None = None) -> sqlite3.Connection:
    """Load every CSV into the SQLite database. Returns the connection."""
    db_path = db_path or DB_PATH
    data_dir = data_dir or DATA_DIR

    conn = get_connection(db_path)

    create_tables(conn)

    csv_table_map: dict[str, str] = {
        "practice_master.csv": "practice_master",
        "practice_infrastructure_requirement.csv": "practice_infrastructure_requirement",
        "practice_cost_profile.csv": "practice_cost_profile",
        "practice_sources.csv": "practice_sources",
        "crop_master.csv": "crop_master",
        "crop_practice_compatibility.csv": "crop_practice_compatibility",
        "crop_location_suitability.csv": "crop_location_suitability",
    }

    for csv_name, table_name in csv_table_map.items():
        _load_csv_into_table(conn, data_dir / csv_name, table_name)

    # Create indexes after data load (idempotent)
    create_indexes(conn)

    # Optional: update SQLite planner statistics
    try:
        conn.execute("ANALYZE")
    except sqlite3.OperationalError:
        pass

    return conn
