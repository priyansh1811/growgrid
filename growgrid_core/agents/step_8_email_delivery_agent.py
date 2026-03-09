"""Agent 11 — Email Delivery Agent (Phase-1 stub).

Purpose: Send the generated report to the user via email.
Supports dry-run mode for development.

Requires:
    - SMTP configuration
    - Report payload from ReportComposerAgent
"""

from __future__ import annotations

import logging
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.utils.types import PlanRequest

logger = logging.getLogger(__name__)


class EmailDeliveryAgent(BaseAgent):
    """Send report via email. (Phase-1 stub with dry-run mode)"""

    def __init__(self, dry_run: bool = True) -> None:
        self._dry_run = dry_run

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        logger.info("EmailDeliveryAgent is a Phase-1 stub — dry_run=%s.", self._dry_run)

        state["email_status"] = {
            "status": "stub" if self._dry_run else "not_implemented",
            "sent": False,
            "timestamp": None,
            "retries": 0,
            "dry_run": self._dry_run,
            "message": "Email delivery not yet implemented. "
            "Will use SMTP with configurable backend.",
        }
        return state
