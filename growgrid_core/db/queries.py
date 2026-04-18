"""Named query functions against the GrowGrid SQLite database."""

from __future__ import annotations

import sqlite3


def _rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    """Convert sqlite3.Row results to plain dicts."""
    return [dict(row) for row in cursor.fetchall()]


# ── Practice queries ─────────────────────────────────────────────────────


def get_all_practices(conn: sqlite3.Connection) -> list[dict]:
    """Return all rows from practice_master."""
    cur = conn.execute("SELECT * FROM practice_master")
    return _rows_to_dicts(cur)


def get_crop_count_by_practice(
    conn: sqlite3.Connection,
    min_compatibility: str = "MED",
) -> dict[str, int]:
    """Return a dict of practice_code -> count of compatible crops.

    Useful for penalizing or eliminating practices with no crop mappings.
    """
    compat_values = ("GOOD",) if min_compatibility == "GOOD" else ("GOOD", "MED")
    placeholders = ",".join("?" for _ in compat_values)

    sql = f"""
        SELECT practice_code, COUNT(DISTINCT crop_id) AS crop_count
        FROM crop_practice_compatibility
        WHERE compatibility IN ({placeholders})
        GROUP BY practice_code
    """
    cur = conn.execute(sql, compat_values)
    return {row["practice_code"]: row["crop_count"] for row in cur.fetchall()}


def get_practice_by_code(conn: sqlite3.Connection, practice_code: str) -> dict | None:
    """Return a single practice row or None."""
    cur = conn.execute(
        "SELECT * FROM practice_master WHERE practice_code = ?",
        (practice_code,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_practice_infrastructure(
    conn: sqlite3.Connection, practice_code: str
) -> list[dict]:
    """Return infrastructure requirements for a practice."""
    cur = conn.execute(
        "SELECT * FROM practice_infrastructure_requirement WHERE practice_code = ?",
        (practice_code,),
    )
    return _rows_to_dicts(cur)


def get_practice_location_suitability(
    conn: sqlite3.Connection,
    practice_code: str,
    state: str | None,
) -> dict | None:
    """Return practice suitability for a state, with ALL as fallback."""
    if state:
        cur = conn.execute(
            """SELECT * FROM practice_location_suitability
               WHERE practice_code = ? AND state = ?""",
            (practice_code, state),
        )
        row = cur.fetchone()
        if row:
            return dict(row)

    cur = conn.execute(
        """SELECT * FROM practice_location_suitability
           WHERE practice_code = ? AND state = 'ALL'""",
        (practice_code,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_practice_irrigation_suitability(
    conn: sqlite3.Connection,
    practice_code: str,
    irrigation_source: str,
) -> dict | None:
    """Return practice suitability for a given irrigation source."""
    cur = conn.execute(
        """SELECT * FROM practice_irrigation_suitability
           WHERE practice_code = ? AND irrigation_source = ?""",
        (practice_code, irrigation_source),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_practice_season_suitability(
    conn: sqlite3.Connection,
    practice_code: str,
    season: str,
) -> dict | None:
    """Return practice suitability for a given season (KHARIF/RABI/ZAID)."""
    cur = conn.execute(
        """SELECT * FROM practice_season_suitability
           WHERE practice_code = ? AND season = ?""",
        (practice_code, season),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_practice_costs(conn: sqlite3.Connection, practice_code: str) -> list[dict]:
    """Return cost profile rows for a practice."""
    cur = conn.execute(
        "SELECT * FROM practice_cost_profile WHERE practice_code = ?",
        (practice_code,),
    )
    return _rows_to_dicts(cur)


# ── Crop queries ─────────────────────────────────────────────────────────


def get_all_crops(conn: sqlite3.Connection) -> list[dict]:
    """Return all rows from crop_master."""
    cur = conn.execute("SELECT * FROM crop_master")
    return _rows_to_dicts(cur)


def get_crop_by_id(conn: sqlite3.Connection, crop_id: str) -> dict | None:
    """Return a single crop row or None."""
    cur = conn.execute(
        "SELECT * FROM crop_master WHERE crop_id = ?",
        (crop_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_crops_for_practice(
    conn: sqlite3.Connection,
    practice_code: str,
    min_compatibility: str = "MED",
) -> list[dict]:
    """Return crops compatible with a practice.

    min_compatibility:
      - "GOOD": only GOOD rows
      - "MED" : GOOD + MED rows (default)
    """
    allowed = {"GOOD", "MED"}
    if min_compatibility not in allowed:
        raise ValueError(
            f"min_compatibility must be one of {sorted(allowed)}; got '{min_compatibility}'"
        )

    compat_values = ("GOOD",) if min_compatibility == "GOOD" else ("GOOD", "MED")
    placeholders = ",".join("?" for _ in compat_values)

    sql = f"""
        SELECT
            cm.*,
            cpc.compatibility,
            cpc.compatibility_score,
            cpc.role_hint,
            cpc.rationale
        FROM crop_practice_compatibility cpc
        JOIN crop_master cm ON cm.crop_id = cpc.crop_id
        WHERE cpc.practice_code = ?
          AND cpc.compatibility IN ({placeholders})
        ORDER BY
            cpc.compatibility_score DESC,
            cm.crop_name ASC,
            cm.crop_id ASC
    """
    cur = conn.execute(sql, (practice_code, *compat_values))
    return _rows_to_dicts(cur)


def get_crop_suitability_for_state(
    conn: sqlite3.Connection, crop_id: str, state: str
) -> dict | None:
    """Return the suitability row for a crop in a given state, or None."""
    cur = conn.execute(
        "SELECT * FROM crop_location_suitability WHERE crop_id = ? AND state = ?",
        (crop_id, state),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_suitability_by_state(
    conn: sqlite3.Connection, state: str
) -> dict[str, dict]:
    """Return all crop suitability rows for a state as crop_id -> row dict."""
    cur = conn.execute(
        "SELECT * FROM crop_location_suitability WHERE state = ?",
        (state.strip(),),
    )
    return {row["crop_id"]: dict(row) for row in cur.fetchall()}


def get_compatibility_score(
    conn: sqlite3.Connection,
    crop_id: str,
    practice_code: str,
) -> float:
    """Return the compatibility score for a crop-practice pair, or 0.0 if not found."""
    cur = conn.execute(
        """SELECT compatibility_score FROM crop_practice_compatibility
           WHERE crop_id = ? AND practice_code = ?""",
        (crop_id, practice_code),
    )
    row = cur.fetchone()
    return float(row["compatibility_score"]) if row else 0.0


# ── Economics queries ───────────────────────────────────────────────────


def get_crop_costs(conn: sqlite3.Connection, crop_id: str) -> list[dict]:
    """Return cost profile rows for a specific crop."""
    cur = conn.execute(
        "SELECT * FROM crop_cost_profile WHERE crop_id = ?",
        (crop_id,),
    )
    return _rows_to_dicts(cur)


def get_yield_bands(conn: sqlite3.Connection, crop_id: str) -> dict | None:
    """Return yield baseline bands for a crop, or None if not found."""
    cur = conn.execute(
        "SELECT * FROM yield_baseline_bands WHERE crop_id = ?",
        (crop_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_yield_state_bands(
    conn: sqlite3.Connection,
    crop_id: str,
    state: str,
    season: str | None = None,
) -> dict | None:
    """Return state-specific yield bands for a crop in a state.

    Lookup priority:
    1. Exact (crop_id, state, season) match
    2. (crop_id, state, 'ANNUAL') — for perennial/whole-year crops
    3. Any (crop_id, state) match — best available season
    4. None — caller should fall back to national yield_baseline_bands

    Returns dict with low/base/high_yield_per_acre, or None.
    """
    # 1. Exact match with season
    if season:
        cur = conn.execute(
            "SELECT * FROM yield_state_bands WHERE crop_id = ? AND UPPER(state) = UPPER(?) AND season = ?",
            (crop_id, state, season),
        )
        row = cur.fetchone()
        if row:
            return dict(row)

    # 2. Try ANNUAL (whole-year crops)
    cur2 = conn.execute(
        "SELECT * FROM yield_state_bands WHERE crop_id = ? AND UPPER(state) = UPPER(?) AND season = 'ANNUAL'",
        (crop_id, state),
    )
    row2 = cur2.fetchone()
    if row2:
        return dict(row2)

    # 3. Any season for this crop+state (best available)
    cur3 = conn.execute(
        "SELECT * FROM yield_state_bands WHERE crop_id = ? AND UPPER(state) = UPPER(?) ORDER BY data_points DESC LIMIT 1",
        (crop_id, state),
    )
    row3 = cur3.fetchone()
    return dict(row3) if row3 else None


def get_price_bands(conn: sqlite3.Connection, crop_id: str) -> dict | None:
    """Return price baseline bands for a crop, or None if not found."""
    cur = conn.execute(
        "SELECT * FROM price_baseline_bands WHERE crop_id = ?",
        (crop_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_loss_factor(conn: sqlite3.Connection, perishability: str) -> dict | None:
    """Return loss factor for a perishability level, or None."""
    cur = conn.execute(
        "SELECT * FROM loss_factor_reference WHERE perishability_level = ?",
        (perishability,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_economics_scenario_reference(
    conn: sqlite3.Connection,
    practice_code: str,
) -> dict | None:
    """Return scenario calibration values for a practice, or None."""
    cur = conn.execute(
        "SELECT * FROM economics_scenario_reference WHERE practice_code = ?",
        (practice_code,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


# ── Irrigation / fertilizer / labour cost queries ──────────────────────


def get_irrigation_costs(
    conn: sqlite3.Connection,
    irrigation_source: str,
) -> dict | None:
    """Return capex_per_acre and opex_per_acre for an irrigation source, or None."""
    cur = conn.execute(
        "SELECT * FROM irrigation_cost_reference WHERE irrigation_source = ?",
        (irrigation_source,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_fertilizer_input_costs(conn: sqlite3.Connection) -> list[dict]:
    """Return all fertilizer input cost rows."""
    cur = conn.execute("SELECT * FROM fertilizer_input_costs")
    return _rows_to_dicts(cur)


def get_crop_labour_share(
    conn: sqlite3.Connection,
    crop_category: str,
) -> float:
    """Return labour share fraction for a crop category, default 0.35."""
    cur = conn.execute(
        "SELECT labour_share_pct FROM crop_labour_share WHERE crop_category = ?",
        (crop_category,),
    )
    row = cur.fetchone()
    if row:
        return float(row["labour_share_pct"])
    # Try DEFAULT fallback
    cur2 = conn.execute(
        "SELECT labour_share_pct FROM crop_labour_share WHERE crop_category = 'DEFAULT'",
    )
    row2 = cur2.fetchone()
    return float(row2["labour_share_pct"]) if row2 else 0.35


def get_best_matching_subsidy(
    conn: sqlite3.Connection,
    practice_code: str,
    state: str,
) -> dict | None:
    """Return the scheme with the highest subsidy_pct matching a practice and state.

    Matches on practice_tags (semicolon-delimited) and state ('ALL' or exact match).
    Returns None if no matching scheme with subsidy_pct > 0 is found.
    """
    # Match schemes where practice_tags contains the practice code
    # and state is 'ALL' or matches the farmer's state
    cur = conn.execute(
        """
        SELECT scheme_id, scheme_name, subsidy_pct, max_subsidy_inr
        FROM schemes_metadata
        WHERE subsidy_pct > 0
          AND (state = 'ALL' OR UPPER(state) = UPPER(?))
          AND (',' || REPLACE(practice_tags, ';', ',') || ',' LIKE '%,' || ? || ',%')
        ORDER BY subsidy_pct DESC
        LIMIT 1
        """,
        (state, practice_code),
    )
    row = cur.fetchone()
    return dict(row) if row else None


# ── Field layout queries ────────────────────────────────────────────────


def get_crop_spacing(
    conn: sqlite3.Connection, crop_id: str, practice_code: str
) -> dict | None:
    """Return spacing reference for a crop-practice pair, or None."""
    cur = conn.execute(
        "SELECT * FROM crop_spacing_reference WHERE crop_id = ? AND practice_code = ?",
        (crop_id, practice_code),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_all_spacings_for_crop(conn: sqlite3.Connection, crop_id: str) -> list[dict]:
    """Return all spacing entries for a crop (across practices)."""
    cur = conn.execute(
        "SELECT * FROM crop_spacing_reference WHERE crop_id = ?",
        (crop_id,),
    )
    return _rows_to_dicts(cur)


# ── Government schemes queries ──────────────────────────────────────────


def get_all_schemes(conn: sqlite3.Connection) -> list[dict]:
    """Return all scheme metadata rows."""
    cur = conn.execute("SELECT * FROM schemes_metadata")
    return _rows_to_dicts(cur)


def get_schemes_for_state(conn: sqlite3.Connection, state: str) -> list[dict]:
    """Return schemes applicable to a state (including ALL = central schemes)."""
    cur = conn.execute(
        "SELECT * FROM schemes_metadata WHERE state = 'ALL' OR state LIKE ?",
        (f"%{state}%",),
    )
    return _rows_to_dicts(cur)


# ── ICAR queries ──────────────────────────────────────────────────────────


def get_icar_crop_calendar(
    conn: sqlite3.Connection,
    state: str,
    season: str,
    crop_name: str,
) -> list[dict]:
    """Return ICAR crop calendar rows matching state, season, and crop name.

    Uses case-insensitive LIKE on crop_name to handle ICAR name variants.
    """
    cur = conn.execute(
        """SELECT * FROM icar_crop_calendar
           WHERE state = ? AND season = ? AND crop_name LIKE ?""",
        (state, season, f"%{crop_name}%"),
    )
    return _rows_to_dicts(cur)


def get_icar_crop_calendar_by_state_season(
    conn: sqlite3.Connection,
    state: str,
    season: str,
) -> list[dict]:
    """Return all ICAR crop calendar rows for a state+season pair."""
    cur = conn.execute(
        "SELECT * FROM icar_crop_calendar WHERE state = ? AND season = ?",
        (state, season),
    )
    return _rows_to_dicts(cur)


def get_icar_nutrient_plan(
    conn: sqlite3.Connection,
    state: str,
    season: str,
    crop_name: str,
) -> list[dict]:
    """Return ICAR nutrient plan rows for a crop in a state+season."""
    cur = conn.execute(
        """SELECT * FROM icar_nutrient_plan
           WHERE state = ? AND season = ? AND crop_name LIKE ?""",
        (state, season, f"%{crop_name}%"),
    )
    return _rows_to_dicts(cur)


def get_icar_pest_disease(
    conn: sqlite3.Connection,
    state: str,
    season: str,
    crop_name: str,
) -> list[dict]:
    """Return ICAR pest/disease rows for a crop in a state+season."""
    cur = conn.execute(
        """SELECT * FROM icar_pest_disease
           WHERE state = ? AND season = ? AND crop_name LIKE ?""",
        (state, season, f"%{crop_name}%"),
    )
    return _rows_to_dicts(cur)


def get_icar_varieties(
    conn: sqlite3.Connection,
    state: str,
    season: str,
    crop_name: str,
) -> list[dict]:
    """Return ICAR variety rows for a crop in a state+season."""
    cur = conn.execute(
        """SELECT * FROM icar_varieties
           WHERE state = ? AND season = ? AND crop_name LIKE ?""",
        (state, season, f"%{crop_name}%"),
    )
    return _rows_to_dicts(cur)


def get_icar_weed_management(
    conn: sqlite3.Connection,
    state: str,
    season: str,
    crop_name: str,
) -> list[dict]:
    """Return ICAR weed management rows for a crop in a state+season."""
    cur = conn.execute(
        """SELECT * FROM icar_weed_management
           WHERE state = ? AND season = ? AND crop_name LIKE ?""",
        (state, season, f"%{crop_name}%"),
    )
    return _rows_to_dicts(cur)
