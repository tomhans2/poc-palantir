from pydantic import BaseModel
from typing import Any, Optional


class SimulateRequest(BaseModel):
    action_id: str
    node_id: str


class InsightItem(BaseModel):
    text: str
    type: str
    severity: str
    source_node: Optional[str] = None
    target_node: Optional[str] = None
    rule_id: Optional[str] = None


class DeltaGraph(BaseModel):
    updated_nodes: list[dict[str, Any]] = []
    highlight_edges: list[dict[str, Any]] = []


class SimulateResponse(BaseModel):
    status: str
    delta_graph: DeltaGraph
    ripple_path: list[str] = []
    insights: list[InsightItem] = []
