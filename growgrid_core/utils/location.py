"""Location parsing helpers."""

from __future__ import annotations


def parse_state_from_location(location: str) -> str | None:
    """Parse the state from a 'State, District' style location string.

    GrowGrid's UI asks for location in 'State, District' order, so the first
    comma-separated token is treated as the state. If only one token is
    provided, that token is returned unchanged.
    """
    if not location or not location.strip():
        return None
    parts = [part.strip() for part in location.strip().split(",") if part.strip()]
    if not parts:
        return None
    return parts[0]
