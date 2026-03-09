"""Abstract base class for all pipeline agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from growgrid_core.utils.types import PlanRequest


class BaseAgent(ABC):
    """Every agent reads from *state*, computes, and writes results back."""

    @abstractmethod
    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        """Execute agent logic.

        Args:
            state: Mutable pipeline state dict updated by prior agents.
            request: The original validated PlanRequest.

        Returns:
            Updated state dict (same object, mutated).
        """
