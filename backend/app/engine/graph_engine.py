"""OntologyEngine — core engine for graph construction, DSL parsing, ripple propagation, and insight generation."""

from __future__ import annotations

import copy
from typing import Any, Optional

import networkx as nx

from app.engine.action_registry import ActionContext, ActionRegistry, ActionResult
from app.engine.event_queue import EventQueue
from app.models.action import Action, RippleRule
from app.models.workspace import WorkspaceConfig


class OntologyEngine:
    """Orchestrates workspace loading, action execution, ripple propagation, and insight generation."""

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self.schema: Optional[dict[str, Any]] = None
        self.initial_snapshot: dict[str, dict[str, Any]] = {}
        self.action_registry: ActionRegistry = ActionRegistry()
        self.event_queue: EventQueue = EventQueue()
        self.insights_feed: list[dict[str, Any]] = []
        self.ripple_path: list[str] = []
        self.updated_nodes: list[dict[str, Any]] = []
        self.highlight_edges: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Workspace loading
    # ------------------------------------------------------------------

    def load_workspace(
        self,
        schema: dict[str, Any],
        action_module: object | None = None,
        custom_action_module: object | None = None,
    ) -> None:
        """Parse *schema* (a WorkspaceConfig-shaped dict) and build the NetworkX graph.

        If *action_module* is provided, scan it for ``@register_action``-decorated
        functions and register them as ``"builtin"`` in the ActionRegistry.

        If *custom_action_module* is provided, scan it for ``@register_action``-decorated
        functions and register them as ``"custom"`` (overriding any builtin with the same name).
        """
        self.graph.clear()
        self.action_registry = ActionRegistry()
        self.insights_feed = []
        self.ripple_path = []
        self.updated_nodes = []
        self.highlight_edges = []

        self.schema = schema

        # --- Build graph ---
        graph_data = schema.get("graph_data", {})
        for node in graph_data.get("nodes", []):
            attrs = {"type": node["type"], **node.get("properties", {})}
            self.graph.add_node(node["id"], **attrs)

        for edge in graph_data.get("edges", []):
            attrs = {"type": edge["type"], **edge.get("properties", {})}
            self.graph.add_edge(edge["source"], edge["target"], **attrs)

        # --- Save initial snapshot (deep copy of all node attributes) ---
        self.initial_snapshot = {
            nid: copy.deepcopy(dict(attrs))
            for nid, attrs in self.graph.nodes(data=True)
        }

        # --- Register action functions (builtin first, custom overrides) ---
        if action_module is not None:
            self.action_registry.register_from_module(action_module, source="builtin")
        if custom_action_module is not None:
            self.action_registry.register_from_module(custom_action_module, source="custom")

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def execute_action(
        self,
        action_id: str,
        target_node_id: str,
    ) -> dict[str, Any]:
        """Execute *action_id* on *target_node_id*, propagate ripple rules, and return structured results."""
        # Reset per-execution accumulators
        self.insights_feed = []
        self.ripple_path = [target_node_id]
        self.updated_nodes = []
        self.highlight_edges = []

        action_def = self._find_action(action_id)
        if action_def is None:
            return {"status": "error", "message": f"Action '{action_id}' not found"}

        # --- Apply direct effect ---
        if action_def.direct_effect is not None:
            prop = action_def.direct_effect.property_to_update
            new_val = action_def.direct_effect.new_value
            if self.graph.has_node(target_node_id):
                old_val = self.graph.nodes[target_node_id].get(prop)
                self.graph.nodes[target_node_id][prop] = new_val
                self.updated_nodes.append({
                    "id": target_node_id,
                    prop: new_val,
                    f"_old_{prop}": old_val,
                })

        # --- Process ripple rules ---
        for rule in action_def.ripple_rules:
            self._process_ripple_rule(rule, target_node_id)

        result = {
            "status": "success",
            "delta_graph": {
                "updated_nodes": self.updated_nodes,
                "highlight_edges": self.highlight_edges,
            },
            "ripple_path": self.ripple_path,
            "insights": self.insights_feed,
        }

        # --- Record event in history ---
        self.event_queue.push(action_id, target_node_id, result)

        return result

    # ------------------------------------------------------------------
    # Ripple rule processing
    # ------------------------------------------------------------------

    def _process_ripple_rule(self, rule: RippleRule, source_node_id: str) -> None:
        """Parse the DSL path, find matching neighbors, evaluate condition, and apply secondary effect."""
        direction, edge_type, node_type = self._parse_propagation_path(rule.propagation_path)

        if direction == "incoming":
            edge_iter = self.graph.in_edges(source_node_id, data=True)
        else:
            edge_iter = self.graph.out_edges(source_node_id, data=True)

        for u, v, edata in edge_iter:
            # Determine neighbor id
            neighbor_id = u if direction == "incoming" else v

            # Filter by edge type
            if edata.get("type") != edge_type:
                continue

            # Filter by node type
            neighbor_attrs = self.graph.nodes.get(neighbor_id, {})
            if neighbor_attrs.get("type") != node_type:
                continue

            # Evaluate condition (if present)
            if rule.condition and not self._eval_condition(rule.condition, source_node_id, neighbor_id):
                continue

            # Record edge highlight
            self.highlight_edges.append({"source": u, "target": v, "type": edata.get("type", "")})

            # Record ripple path
            if neighbor_id not in self.ripple_path:
                self.ripple_path.append(neighbor_id)

            # Apply secondary effect
            self._apply_secondary_effect(rule, source_node_id, neighbor_id)

    def _parse_propagation_path(self, path: str) -> tuple[str, str, str]:
        """Parse Cypher-style DSL like ``'<-[EDGE_TYPE]- NodeType'`` or ``'-[EDGE_TYPE]-> NodeType'``.

        Returns ``(direction, edge_type, node_type)`` where direction is
        ``'incoming'`` or ``'outgoing'``.
        """
        if path.startswith("<-"):
            direction = "incoming"
        else:
            direction = "outgoing"

        # Extract edge type between [ and ]
        edge_type = path.split("[")[1].split("]")[0]

        # Extract node type after the closing "]" portion.
        # Incoming: "<-[TYPE]- NodeType"  — after "]" we have "- NodeType"
        # Outgoing: "-[TYPE]-> NodeType"  — after "]" we have "-> NodeType"
        after_bracket = path.split("]")[1]  # e.g. "- Company" or "-> Company"
        # Strip leading dashes, arrows, and spaces
        node_type = after_bracket.lstrip("-").lstrip(">").strip()

        return direction, edge_type, node_type

    def _eval_condition(self, condition: str, source_id: str, target_id: str) -> bool:
        """Evaluate a condition expression against source and target node attributes.

        Uses a restricted ``eval`` with source/target dicts exposed as ``source`` and ``target``.
        """
        source_attrs = dict(self.graph.nodes.get(source_id, {}))
        target_attrs = dict(self.graph.nodes.get(target_id, {}))
        try:
            return bool(eval(condition, {"__builtins__": {}}, {"source": source_attrs, "target": target_attrs}))
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Secondary effect application
    # ------------------------------------------------------------------

    def _apply_secondary_effect(
        self,
        rule: RippleRule,
        source_node_id: str,
        target_node_id: str,
    ) -> None:
        """Look up the triggered function, build ActionContext, execute it, and write back results."""
        func_name = rule.effect_on_target.action_to_trigger
        params = dict(rule.effect_on_target.parameters)

        func = self.action_registry.get(func_name)
        if func is None:
            # Unknown function — record a warning insight but continue
            self.insights_feed.append({
                "text": f"Warning: action function '{func_name}' not registered",
                "type": "warning",
                "severity": "warning",
                "source_node": source_node_id,
                "target_node": target_node_id,
                "rule_id": rule.rule_id,
            })
            return

        target_attrs = dict(self.graph.nodes.get(target_node_id, {}))
        source_attrs = dict(self.graph.nodes.get(source_node_id, {}))

        ctx = ActionContext(
            target_node=target_attrs,
            source_node=source_attrs,
            target_id=target_node_id,
            source_id=source_node_id,
            params=params,
            graph=self.graph,
        )

        result: ActionResult = func(ctx)

        # Write updated properties back to the graph
        for prop, value in result.updated_properties.items():
            self.graph.nodes[target_node_id][prop] = value

        # Record updated node
        node_update: dict[str, Any] = {"id": target_node_id}
        node_update.update(result.updated_properties)
        for k, v in result.old_values.items():
            node_update[f"_old_{k}"] = v
        self.updated_nodes.append(node_update)

        # Generate insight
        self._generate_insight(rule, source_node_id, target_node_id)

    # ------------------------------------------------------------------
    # Insight generation
    # ------------------------------------------------------------------

    def _generate_insight(
        self,
        rule: RippleRule,
        source_node_id: str,
        target_node_id: str,
    ) -> None:
        """Create a structured insight object using the rule's template, type, and severity."""
        insight_type = rule.insight_type or "info"
        insight_severity = rule.insight_severity or "info"

        text = ""
        if rule.insight_template:
            source_attrs = dict(self.graph.nodes.get(source_node_id, {}))
            target_attrs = dict(self.graph.nodes.get(target_node_id, {}))
            try:
                text = rule.insight_template.format_map(
                    {"source": source_attrs, "target": target_attrs}
                )
            except (KeyError, IndexError):
                text = rule.insight_template
        else:
            text = f"Rule {rule.rule_id}: effect applied to {target_node_id}"

        self.insights_feed.append({
            "text": text,
            "type": insight_type,
            "severity": insight_severity,
            "source_node": source_node_id,
            "target_node": target_node_id,
            "rule_id": rule.rule_id,
        })

    # ------------------------------------------------------------------
    # Graph export
    # ------------------------------------------------------------------

    def get_graph_for_render(self) -> dict[str, Any]:
        """Export graph data in a frontend-friendly nested format.

        Returns ``{nodes: [{id, type, properties: {...}}, ...], edges: [{source, target, type, properties: {...}}, ...]}``
        matching the frontend's ``GraphData`` TypeScript type.
        """
        nodes = []
        for nid, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("type", "")
            properties = {k: v for k, v in attrs.items() if k != "type"}
            nodes.append({"id": nid, "type": node_type, "properties": properties})

        edges = []
        for u, v, attrs in self.graph.edges(data=True):
            edge_type = attrs.get("type", "")
            properties = {k: v for k, v in attrs.items() if k != "type"}
            edges.append({"source": u, "target": v, "type": edge_type, "properties": properties})

        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # Available actions
    # ------------------------------------------------------------------

    def get_available_actions(self, node_id: str | None = None) -> list[dict[str, Any]]:
        """Return actions that are applicable to *node_id* (filtered by node type)."""
        actions = self.schema.get("action_engine", {}).get("actions", []) if self.schema else []

        if node_id is None:
            return [self._action_to_dict(a) for a in actions]

        node_type = self.graph.nodes.get(node_id, {}).get("type")
        if node_type is None:
            return []

        return [
            self._action_to_dict(a)
            for a in actions
            if a.get("target_node_type") == node_type
                or (hasattr(a, "target_node_type") and a.target_node_type == node_type)
        ]

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Restore all node attributes to the initial snapshot taken at load time."""
        for nid, snapshot_attrs in self.initial_snapshot.items():
            if self.graph.has_node(nid):
                # Clear current attrs and replace with snapshot
                current = self.graph.nodes[nid]
                current.clear()
                current.update(copy.deepcopy(snapshot_attrs))

        self.insights_feed = []
        self.ripple_path = []
        self.updated_nodes = []
        self.highlight_edges = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_action(self, action_id: str) -> Action | None:
        """Look up an action definition by ID from the loaded schema."""
        if self.schema is None:
            return None
        actions = self.schema.get("action_engine", {}).get("actions", [])
        for a in actions:
            # Support both dict and Pydantic model objects
            aid = a.get("action_id") if isinstance(a, dict) else a.action_id
            if aid == action_id:
                if isinstance(a, dict):
                    return Action(**a)
                return a
        return None

    @staticmethod
    def _action_to_dict(a: Any) -> dict[str, Any]:
        if isinstance(a, dict):
            return a
        return a.model_dump() if hasattr(a, "model_dump") else dict(a)
