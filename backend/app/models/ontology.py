from pydantic import BaseModel
from typing import Optional


class NodeTypeDef(BaseModel):
    label: str
    color: str
    shape: str
    icon: Optional[str] = None
    properties: Optional[dict] = None


class EdgeTypeDef(BaseModel):
    label: str
    color: str
    style: Optional[str] = None
    properties: Optional[dict] = None


class OntologyDef(BaseModel):
    node_types: dict[str, NodeTypeDef]
    edge_types: dict[str, EdgeTypeDef]
