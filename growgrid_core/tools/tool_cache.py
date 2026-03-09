"""Tavily result cache backed by SQLite.

Cache key format: "{location}|{practice_code}|{crop_id}|{season}|v1"
TTL default: 168 hours (7 days).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from growgrid_core.config import CACHE_DIR, CACHE_TTL_HOURS

_DDL = """
CREATE TABLE IF NOT EXISTS tool_cache (
    cache_key   TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    ttl_hours   INTEGER NOT NULL DEFAULT 168
)
"""


class ToolCache:
    """Simple SQLite-backed cache for external API results."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            db_path = CACHE_DIR / "tavily_cache.db"
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(_DDL)
        self._conn.commit()

    def get(self, key: str) -> list[dict[str, Any]] | None:
        """Return cached payload if fresh, else None."""
        row = self._conn.execute(
            "SELECT payload_json, created_at, ttl_hours FROM tool_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None

        payload_json, created_str, ttl_hours = row
        created = datetime.fromisoformat(created_str)
        if datetime.now(timezone.utc) - created > timedelta(hours=ttl_hours):
            # Stale — delete and return None
            self._conn.execute("DELETE FROM tool_cache WHERE cache_key = ?", (key,))
            self._conn.commit()
            return None

        return json.loads(payload_json)

    def set(self, key: str, payload: list[dict[str, Any]], ttl_hours: int | None = None) -> None:
        """Store payload in cache (upsert)."""
        ttl = ttl_hours if ttl_hours is not None else CACHE_TTL_HOURS
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO tool_cache (cache_key, payload_json, created_at, ttl_hours)
               VALUES (?, ?, ?, ?)""",
            (key, json.dumps(payload), now, ttl),
        )
        self._conn.commit()

    def is_fresh(self, key: str, max_age_hours: int | None = None) -> bool:
        """Check if a key exists and is fresh."""
        row = self._conn.execute(
            "SELECT created_at, ttl_hours FROM tool_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return False
        created_str, ttl = row
        effective_ttl = max_age_hours or ttl
        created = datetime.fromisoformat(created_str)
        return datetime.now(timezone.utc) - created <= timedelta(hours=effective_ttl)

    def close(self) -> None:
        self._conn.close()
