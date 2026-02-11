from pydantic import BaseModel
from typing import Optional
from .ontology import OntologyDef
from .graph import GraphData
from .action import ActionEngine


class Metadata(BaseModel):
    domain: str
    version: Optional[str] = None
    description: Optional[str] = None


class WorkspaceConfig(BaseModel):
    metadata: Metadata
    ontology_def: OntologyDef
    graph_data: GraphData
    action_engine: ActionEngine
