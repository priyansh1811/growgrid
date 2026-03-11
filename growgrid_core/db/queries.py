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
