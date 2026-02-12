"""REST API routes for the workspace — load, simulate, reset, history, samples."""

from __future__ import annotations

import importlib.util
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import ValidationError

from app.actions import action_functions
from app.engine.graph_engine import OntologyEngine
from app.models.api import SimulateRequest, SimulateResponse, InsightItem, DeltaGraph, GraphData
from app.models.workspace import WorkspaceConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workspace")

# --- Module-level singletons ---
engine = OntologyEngine()

# --- Samples directory (resolved relative to project root) ---
SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _check_unregistered_functions(data: dict[str, Any]) -> list[str]:
    """Check all action_to_trigger references against the registry.

    Returns a list of warning strings for any unregistered function names.
    """
    warnings: list[str] = []
    actions = data.get("action_engine", {}).get("actions", [])
    for action in actions:
        for rule in action.get("ripple_rules", []):
            func_name = rule.get("effect_on_target", {}).get("action_to_trigger")
            if func_name and engine.action_registry.get(func_name) is None:
                warnings.append(
                    f"Function '{func_name}' referenced in rule '{rule.get('rule_id', '?')}' "
                    f"is not registered in ActionRegistry"
                )
    return warnings


def _load_sample_data(sample_name: str) -> dict[str, Any]:
    """Load a built-in sample JSON file by name (without .json extension)."""
    sample_path = SAMPLES_DIR / f"{sample_name}.json"
    if not sample_path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Sample '{sample_name}' not found. Available samples: "
                   f"{[p.stem for p in sorted(SAMPLES_DIR.glob('*.json'))]}",
        )
    try:
        return json.loads(sample_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=f"Sample file '{sample_name}.json' contains invalid JSON: {exc}"
        ) from exc


def _load_module_from_path(path: Path, module_name: str = "custom_actions") -> object:
    """Dynamically load a Python module from a file path using importlib."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise HTTPException(status_code=400, detail=f"Cannot load Python module from '{path}'")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_convention_action_file(sample_name: str) -> Path | None:
    """Check for a convention-based .py file alongside the sample JSON."""
    py_path = SAMPLES_DIR / f"{sample_name}.py"
    if py_path.is_file():
        return py_path
    return None


# ------------------------------------------------------------------
# GET /samples
# ------------------------------------------------------------------

@router.get("/samples")
async def list_samples() -> list[dict[str, str]]:
    """Return a list of available built-in sample files from the samples/ directory."""
    if not SAMPLES_DIR.is_dir():
        return []
    results = []
    for path in sorted(SAMPLES_DIR.glob("*.json")):
        # Read description from the JSON metadata if available
        description = ""
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            description = content.get("metadata", {}).get("description", "")
        except Exception:
            pass
        results.append({"name": path.stem, "description": description})
    return results


# ------------------------------------------------------------------
# POST /load
# ------------------------------------------------------------------

@router.post("/load")
async def load_workspace(
    file: UploadFile | None = File(None),
    action_file: UploadFile | None = File(None),
    sample: str | None = None,
) -> dict[str, Any]:
    """Load a workspace from an uploaded JSON file or a built-in sample name.

    Accepts either:
    - A multipart/form-data file upload (``file``), or
    - A query parameter ``sample`` naming a built-in scenario (e.g. ``corporate_acquisition``).

    Optionally accepts a second file upload (``action_file``) containing custom
    ``@register_action``-decorated Python functions. Custom functions override
    builtin functions with the same name.

    When loading a sample, the system also checks for a convention-based Python file
    at ``samples/<sample_name>.py`` and auto-loads it if present.

    Returns metadata, ontology_def, graph_data, actions, registered_functions (with source), and warnings.
    """
    custom_module = None
    sample_name: str | None = None

    if file is not None:
        # --- File upload path ---
        try:
            raw = await file.read()
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    elif sample is not None:
        # --- Built-in sample path ---
        sample_name = sample
        data = _load_sample_data(sample)
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or a 'sample' query parameter.")

    # Validate via Pydantic — return 422 with field-level errors
    try:
        WorkspaceConfig(**data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    # --- Resolve custom action module ---
    # Priority 1: explicit action_file upload (overrides convention)
    if action_file is not None:
        raw_py = await action_file.read()
        # Write to a temp file so importlib can load it
        tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="wb")
        tmp.write(raw_py)
        tmp.flush()
        tmp.close()
        try:
            custom_module = _load_module_from_path(Path(tmp.name), module_name="uploaded_actions")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to load custom action file: {exc}") from exc
    # Priority 2: convention-based .py file alongside sample JSON
    elif sample_name is not None:
        convention_path = _find_convention_action_file(sample_name)
        if convention_path is not None:
            try:
                custom_module = _load_module_from_path(convention_path, module_name=f"sample_{sample_name}_actions")
            except Exception as exc:
                logger.warning("Failed to load convention action file %s: %s", convention_path, exc)

    # Load into engine (idempotent — load_workspace clears previous state)
    engine.load_workspace(data, action_module=action_functions, custom_action_module=custom_module)

    # Log registered functions with sources
    for entry in engine.action_registry.list_actions_with_source():
        logger.info("Registered action: %s (source: %s)", entry["name"], entry["source"])

    # Check for unregistered function references
    warnings = _check_unregistered_functions(data)
    if warnings:
        for w in warnings:
            logger.warning(w)

    # Build registered_functions list with source info
    registered_functions = engine.action_registry.list_actions_with_source()

    return {
        "metadata": data.get("metadata"),
        "ontology_def": data.get("ontology_def"),
        "graph_data": engine.get_graph_for_render(),
        "actions": [
            engine._action_to_dict(a)
            for a in data.get("action_engine", {}).get("actions", [])
        ],
        "registered_functions": registered_functions,
        "warnings": warnings,
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

    # Get the latest graph data after simulation (reflects updated properties)
    updated_graph = engine.get_graph_for_render()

    return SimulateResponse(
        status=result["status"],
        delta_graph=DeltaGraph(**result["delta_graph"]),
        ripple_path=result.get("ripple_path", []),
        insights=[InsightItem(**i) for i in result.get("insights", [])],
        updated_graph_data=GraphData(**updated_graph),
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
