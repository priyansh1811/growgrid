"""Tests for the Tavily result cache."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from growgrid_core.tools.tool_cache import ToolCache


@pytest.fixture
def cache(tmp_path) -> ToolCache:
    return ToolCache(db_path=tmp_path / "test_cache.db")


class TestToolCache:
    def test_set_and_get(self, cache: ToolCache):
        payload = [{"title": "Test", "url": "https://test.com", "content": "test"}]
        cache.set("key1", payload)
        result = cache.get("key1")
        assert result == payload

    def test_get_missing_key_returns_none(self, cache: ToolCache):
        assert cache.get("nonexistent") is None

    def test_is_fresh_for_new_key(self, cache: ToolCache):
        cache.set("key1", [{"data": "test"}])
        assert cache.is_fresh("key1")

    def test_is_fresh_missing_key(self, cache: ToolCache):
        assert not cache.is_fresh("nonexistent")

    def test_stale_entry_via_get(self, cache: ToolCache):
        """Entry with TTL=0 hours: get() should return None once time advances.
        We manipulate created_at directly for a reliable test."""
        cache.set("key1", [{"data": "test"}], ttl_hours=0)
        # Manually backdate the entry so it's clearly stale
        old_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        cache._conn.execute(
            "UPDATE tool_cache SET created_at = ? WHERE cache_key = ?",
            (old_time, "key1"),
        )
        cache._conn.commit()
        # Now it should be stale
        assert cache.get("key1") is None

    def test_overwrite_existing_key(self, cache: ToolCache):
        cache.set("key1", [{"v": 1}])
        cache.set("key1", [{"v": 2}])
        result = cache.get("key1")
        assert result == [{"v": 2}]

    def test_multiple_keys(self, cache: ToolCache):
        cache.set("key1", [{"a": 1}])
        cache.set("key2", [{"b": 2}])
        assert cache.get("key1") == [{"a": 1}]
        assert cache.get("key2") == [{"b": 2}]
