"""REST API routes for the workspace — load, simulate, reset, history."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.actions import action_functions
from app.engine.graph_engine import OntologyEngine
from app.models.api import SimulateRequest, SimulateResponse, InsightItem, DeltaGraph
from app.models.workspace import WorkspaceConfig

router = APIRouter(prefix="/api/v1/workspace")

# --- Module-level singletons ---
engine = OntologyEngine()


# ------------------------------------------------------------------
# POST /load
# ------------------------------------------------------------------

@router.post("/load")
async def load_workspace(
    file: UploadFile | None = File(None),
    sample: str | None = None,
) -> dict[str, Any]:
    """Load a workspace from an uploaded JSON file or a built-in sample name.

    Accepts either:
    - A multipart/form-data file upload (``file``), or
    - A query parameter ``sample`` naming a built-in scenario (e.g. ``corporate_acquisition``).
    """
    if file is not None:
        # --- File upload path ---
        try:
            raw = await file.read()
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    elif sample is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Built-in sample '{sample}' loading not yet implemented. Upload a JSON file instead.",
        )
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or a 'sample' query parameter.")

    # Validate via Pydantic
    try:
        WorkspaceConfig(**data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Schema validation failed: {exc}") from exc

    # Load into engine
    engine.load_workspace(data, action_module=action_functions)

    return {
        "metadata": data.get("metadata"),
        "ontology_def": data.get("ontology_def"),
        "graph_data": engine.get_graph_for_render(),
        "actions": [
            engine._action_to_dict(a)
            for a in data.get("action_engine", {}).get("actions", [])
        ],
    }


# ------------------------------------------------------------------
# POST /simulate
# ------------------------------------------------------------------

@router.post("/simulate", response_model=SimulateResponse)
async def simulate(request: SimulateRequest) -> SimulateResponse:
    """Execute a simulation action on a target node."""
    if engine.schema is None:
        raise HTTPException(status_code=400, detail="No workspace loaded. Call /load first.")

    if not engine.graph.has_node(request.node_id):
        raise HTTPException(status_code=400, detail=f"Node '{request.node_id}' not found in graph.")

    result = engine.execute_action(request.action_id, request.node_id)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Action execution failed"))

    return SimulateResponse(
        status=result["status"],
        delta_graph=DeltaGraph(**result["delta_graph"]),
        ripple_path=result.get("ripple_path", []),
        insights=[InsightItem(**i) for i in result.get("insights", [])],
    )


# ------------------------------------------------------------------
# POST /reset
# ------------------------------------------------------------------

@router.post("/reset")
async def reset_workspace() -> dict[str, Any]:
    """Reset the engine to initial state and clear event history."""
    if engine.schema is None:
        raise HTTPException(status_code=400, detail="No workspace loaded. Call /load first.")

    engine.reset()
    engine.event_queue.clear()

    return engine.get_graph_for_render()


# ------------------------------------------------------------------
# GET /history
# ------------------------------------------------------------------

@router.get("/history")
async def get_history() -> list[dict[str, Any]]:
    """Return the simulation event history."""
    return engine.event_queue.get_history()
