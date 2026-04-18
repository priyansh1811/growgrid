"""Season detection utility for Indian agriculture.

Kharif (monsoon): June–October (months 6-10)
Rabi (winter): November–May (months 11-12, 1-5)
"""

from __future__ import annotations


def detect_season(planning_month: int | None) -> str:
    """Return 'kharif' or 'rabi' based on planning month.

    Months 6-10 = kharif (monsoon season crops)
    Months 1-5, 11-12 = rabi (winter season crops)
    Default (None) = 'rabi' (safer default for year-round planning)
    """
    if planning_month is None:
        return "rabi"
    if planning_month in (6, 7, 8, 9, 10):
        return "kharif"
    return "rabi"


def month_in_sowing_window(
    month: int,
    sow_start: int | None,
    sow_end: int | None,
) -> float:
    """Return a multiplier (0.0–1.0) based on how well a month fits a sowing window.

    - Within window: 1.0
    - Within 1 month of window: 0.85
    - Outside by 2+ months: 0.5
    - No sowing data: 1.0 (no penalty)
    """
    if sow_start is None or sow_end is None:
        return 1.0

    if not (1 <= month <= 12):
        return 1.0

    # Handle wrap-around sowing windows (e.g., Nov-Feb = 11,12,1,2)
    if sow_start <= sow_end:
        window = set(range(sow_start, sow_end + 1))
    else:
        window = set(range(sow_start, 13)) | set(range(1, sow_end + 1))

    if month in window:
        return 1.0

    # Check if within 1 month of the window edges
    near = set()
    for m in window:
        near.add((m % 12) + 1)  # month after
        near.add(((m - 2) % 12) + 1)  # month before
    near -= window

    if month in near:
        return 0.85

    return 0.5
