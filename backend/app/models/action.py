from pydantic import BaseModel
from typing import Any, Optional


class DirectEffect(BaseModel):
    property_to_update: str
    new_value: Any


class EffectOnTarget(BaseModel):
    action_to_trigger: str
    parameters: dict[str, Any] = {}


class RippleRule(BaseModel):
    rule_id: str
    propagation_path: str
    condition: Optional[str] = None
    effect_on_target: EffectOnTarget
    insight_template: Optional[str] = None
    insight_type: Optional[str] = None
    insight_severity: Optional[str] = None


class Action(BaseModel):
    action_id: str
    target_node_type: str
    display_name: str
    direct_effect: Optional[DirectEffect] = None
    ripple_rules: list[RippleRule] = []


class ActionEngine(BaseModel):
    actions: list[Action] = []
