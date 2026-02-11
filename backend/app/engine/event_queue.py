"""EventQueue — records all simulation events for history and replay."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SimulationEvent:
    """A single simulation event record."""

    timestamp: str
    action_id: str
    target_node_id: str
    ripple_path: list[str]
    insights: list[dict[str, Any]]
    delta_graph: dict[str, Any]


class EventQueue:
    """Stores simulation event history in chronological order."""

    def __init__(self) -> None:
        self._events: list[SimulationEvent] = []

    def push(
        self,
        action_id: str,
        target_node_id: str,
        result: dict[str, Any],
    ) -> None:
        """Record a simulation event with an auto-generated ISO timestamp."""
        event = SimulationEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_id=action_id,
            target_node_id=target_node_id,
            ripple_path=result.get("ripple_path", []),
            insights=result.get("insights", []),
            delta_graph=result.get("delta_graph", {}),
        )
        self._events.append(event)

    def get_history(self) -> list[dict[str, Any]]:
        """Return all events as a list of dicts, in chronological order."""
        return [
            {
                "timestamp": e.timestamp,
                "action_id": e.action_id,
                "target_node_id": e.target_node_id,
                "ripple_path": e.ripple_path,
                "insights": e.insights,
                "delta_graph": e.delta_graph,
            }
            for e in self._events
        ]

    def clear(self) -> None:
        """Remove all events."""
        self._events.clear()
