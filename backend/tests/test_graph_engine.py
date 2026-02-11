"""Tests for OntologyEngine — graph construction, DSL parsing, ripple propagation, and insight generation."""

import copy
import types

import pytest

from app.engine.action_registry import ActionContext, ActionResult, register_action
from app.engine.graph_engine import OntologyEngine


# ---------------------------------------------------------------------------
# Helpers – reusable sample data
# ---------------------------------------------------------------------------


def _build_sample_schema() -> dict:
    """Return a minimal but realistic WorkspaceConfig-shaped dict for testing."""
    return {
        "metadata": {
            "domain": "corporate_risk",
            "version": "1.0",
            "description": "Test schema",
        },
        "ontology_def": {
            "node_types": {
                "Company": {"label": "公司", "color": "#4A90D9", "shape": "circle"},
                "Event_Acquisition": {"label": "收购事件", "color": "#F5A623", "shape": "diamond"},
            },
            "edge_types": {
                "ACQUIRES": {"label": "收购", "color": "#666", "style": "solid"},
                "TARGET_OF": {"label": "被收购", "color": "#999", "style": "dashed"},
                "SUPPLIES_TO": {"label": "供应", "color": "#5CB85C", "style": "solid"},
            },
        },
        "graph_data": {
            "nodes": [
                {"id": "C_ALPHA", "type": "Company", "properties": {"name": "Alpha Corp", "valuation": 10000000, "risk_status": "NORMAL"}},
                {"id": "C_BETA", "type": "Company", "properties": {"name": "Beta Inc", "valuation": 5000000, "risk_status": "NORMAL"}},
                {"id": "C_GAMMA", "type": "Company", "properties": {"name": "Gamma Ltd", "valuation": 3000000, "risk_status": "NORMAL"}},
                {"id": "E_ACQ_101", "type": "Event_Acquisition", "properties": {"date": "2024-01-15", "status": "PENDING", "deal_size": 8000000}},
            ],
            "edges": [
                {"source": "C_ALPHA", "target": "E_ACQ_101", "type": "ACQUIRES", "properties": {}},
                {"source": "C_BETA", "target": "E_ACQ_101", "type": "TARGET_OF", "properties": {}},
                {"source": "C_GAMMA", "target": "C_ALPHA", "type": "SUPPLIES_TO", "properties": {"dependency_weight": 0.6}},
                {"source": "C_GAMMA", "target": "C_BETA", "type": "SUPPLIES_TO", "properties": {"dependency_weight": 0.4}},
            ],
        },
        "action_engine": {
            "actions": [
                {
                    "action_id": "trigger_acquisition_failure",
                    "target_node_type": "Event_Acquisition",
                    "display_name": "模拟收购失败事件",
                    "direct_effect": {"property_to_update": "status", "new_value": "FAILED"},
                    "ripple_rules": [
                        {
                            "rule_id": "R001",
                            "propagation_path": "<-[ACQUIRES]- Company",
                            "condition": None,
                            "effect_on_target": {
                                "action_to_trigger": "recalculate_valuation",
                                "parameters": {"shock_factor": -0.3},
                            },
                            "insight_template": "收购失败导致 {target[name]} 估值从 {target[valuation]} 重估",
                            "insight_type": "quantitative_impact",
                            "insight_severity": "critical",
                        },
                        {
                            "rule_id": "R002",
                            "propagation_path": "<-[TARGET_OF]- Company",
                            "condition": None,
                            "effect_on_target": {
                                "action_to_trigger": "update_risk_status",
                                "parameters": {"status": "HIGH_RISK"},
                            },
                            "insight_template": "{target[name]} 作为被收购方风险状态升级为 HIGH_RISK",
                            "insight_type": "risk_propagation",
                            "insight_severity": "warning",
                        },
                        {
                            "rule_id": "R003",
                            "propagation_path": "<-[TARGET_OF]- Company",
                            "condition": None,
                            "effect_on_target": {
                                "action_to_trigger": "adjust_numeric",
                                "parameters": {"property": "valuation", "factor": 0.8},
                            },
                            "insight_template": "{target[name]} 估值因收购失败下调 20%",
                            "insight_type": "quantitative_impact",
                            "insight_severity": "warning",
                        },
                    ],
                },
                {
                    "action_id": "trigger_acquisition_success",
                    "target_node_type": "Event_Acquisition",
                    "display_name": "模拟收购成功事件",
                    "direct_effect": {"property_to_update": "status", "new_value": "COMPLETED"},
                    "ripple_rules": [],
                },
            ],
        },
    }


def _make_action_module():
    """Build a fake module containing action functions for testing."""
    mod = types.ModuleType("test_actions")

    @register_action
    def set_property(ctx: ActionContext) -> ActionResult:
        prop = ctx.params["property"]
        value = ctx.params["value"]
        old_value = ctx.target_node.get(prop)
        return ActionResult(updated_properties={prop: value}, old_values={prop: old_value})

    @register_action
    def adjust_numeric(ctx: ActionContext) -> ActionResult:
        prop = ctx.params["property"]
        factor = ctx.params["factor"]
        old_value = ctx.target_node.get(prop, 0)
        new_value = old_value * factor
        return ActionResult(updated_properties={prop: new_value}, old_values={prop: old_value})

    @register_action
    def recalculate_valuation(ctx: ActionContext) -> ActionResult:
        old_val = ctx.target_node.get("valuation", 0)
        shock_factor = ctx.params.get("shock_factor", 0)
        new_val = old_val * (1 + shock_factor)
        return ActionResult(updated_properties={"valuation": new_val}, old_values={"valuation": old_val})

    @register_action
    def update_risk_status(ctx: ActionContext) -> ActionResult:
        new_status = ctx.params.get("status", "HIGH_RISK")
        old_status = ctx.target_node.get("risk_status")
        return ActionResult(updated_properties={"risk_status": new_status}, old_values={"risk_status": old_status})

    @register_action
    def graph_weighted_exposure(ctx: ActionContext) -> ActionResult:
        old_exposure = ctx.target_node.get("exposure", 0)
        return ActionResult(updated_properties={"exposure": 999}, old_values={"exposure": old_exposure})

    mod.set_property = set_property
    mod.adjust_numeric = adjust_numeric
    mod.recalculate_valuation = recalculate_valuation
    mod.update_risk_status = update_risk_status
    mod.graph_weighted_exposure = graph_weighted_exposure
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return OntologyEngine()


@pytest.fixture
def loaded_engine():
    eng = OntologyEngine()
    eng.load_workspace(_build_sample_schema(), action_module=_make_action_module())
    return eng


# ---------------------------------------------------------------------------
# Tests: load_workspace / graph construction
# ---------------------------------------------------------------------------


class TestLoadWorkspace:
    def test_graph_node_count(self, loaded_engine: OntologyEngine):
        assert loaded_engine.graph.number_of_nodes() == 4

    def test_graph_edge_count(self, loaded_engine: OntologyEngine):
        assert loaded_engine.graph.number_of_edges() == 4

    def test_node_attributes_expanded(self, loaded_engine: OntologyEngine):
        attrs = loaded_engine.graph.nodes["C_ALPHA"]
        assert attrs["type"] == "Company"
        assert attrs["name"] == "Alpha Corp"
        assert attrs["valuation"] == 10000000

    def test_edge_attributes_expanded(self, loaded_engine: OntologyEngine):
        edata = loaded_engine.graph.edges["C_ALPHA", "E_ACQ_101"]
        assert edata["type"] == "ACQUIRES"

    def test_initial_snapshot_saved(self, loaded_engine: OntologyEngine):
        assert "C_ALPHA" in loaded_engine.initial_snapshot
        assert loaded_engine.initial_snapshot["C_ALPHA"]["valuation"] == 10000000

    def test_action_registry_populated(self, loaded_engine: OntologyEngine):
        names = loaded_engine.action_registry.list_actions()
        assert "recalculate_valuation" in names
        assert "update_risk_status" in names

    def test_schema_stored(self, loaded_engine: OntologyEngine):
        assert loaded_engine.schema is not None
        assert loaded_engine.schema["metadata"]["domain"] == "corporate_risk"

    def test_load_without_action_module(self, engine: OntologyEngine):
        engine.load_workspace(_build_sample_schema())
        assert engine.graph.number_of_nodes() == 4
        assert engine.action_registry.list_actions() == []

    def test_load_idempotent(self, engine: OntologyEngine):
        """Multiple loads should reset state completely."""
        mod = _make_action_module()
        engine.load_workspace(_build_sample_schema(), action_module=mod)
        assert engine.graph.number_of_nodes() == 4

        # Load again with a smaller schema
        small_schema = {
            "metadata": {"domain": "test"},
            "ontology_def": {"node_types": {}, "edge_types": {}},
            "graph_data": {
                "nodes": [{"id": "X", "type": "T", "properties": {}}],
                "edges": [],
            },
            "action_engine": {"actions": []},
        }
        engine.load_workspace(small_schema)
        assert engine.graph.number_of_nodes() == 1


# ---------------------------------------------------------------------------
# Tests: DSL path parsing
# ---------------------------------------------------------------------------


class TestDSLParsing:
    def test_incoming_path(self, engine: OntologyEngine):
        direction, edge_type, node_type = engine._parse_propagation_path("<-[TARGET_OF]- Company")
        assert direction == "incoming"
        assert edge_type == "TARGET_OF"
        assert node_type == "Company"

    def test_outgoing_path(self, engine: OntologyEngine):
        direction, edge_type, node_type = engine._parse_propagation_path("-[ACQUIRES]-> Company")
        assert direction == "outgoing"
        assert edge_type == "ACQUIRES"
        assert node_type == "Company"

    def test_incoming_supplies_to(self, engine: OntologyEngine):
        direction, edge_type, node_type = engine._parse_propagation_path("<-[SUPPLIES_TO]- Company")
        assert direction == "incoming"
        assert edge_type == "SUPPLIES_TO"
        assert node_type == "Company"

    def test_outgoing_with_underscore_types(self, engine: OntologyEngine):
        direction, edge_type, node_type = engine._parse_propagation_path("-[HAS_SUBSIDIARY]-> Event_Acquisition")
        assert direction == "outgoing"
        assert edge_type == "HAS_SUBSIDIARY"
        assert node_type == "Event_Acquisition"


# ---------------------------------------------------------------------------
# Tests: execute_action
# ---------------------------------------------------------------------------


class TestExecuteAction:
    def test_basic_execution_returns_success(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        assert result["status"] == "success"

    def test_direct_effect_applied(self, loaded_engine: OntologyEngine):
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        assert loaded_engine.graph.nodes["E_ACQ_101"]["status"] == "FAILED"

    def test_ripple_path_contains_source_and_affected(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        path = result["ripple_path"]
        assert "E_ACQ_101" in path
        assert "C_ALPHA" in path  # ACQUIRES -> Company
        assert "C_BETA" in path   # TARGET_OF -> Company
        assert len(path) >= 3

    def test_insights_are_structured(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        insights = result["insights"]
        assert len(insights) >= 3
        for insight in insights:
            assert "text" in insight
            assert "type" in insight
            assert "severity" in insight
            assert "source_node" in insight
            assert "target_node" in insight
            assert "rule_id" in insight

    def test_insights_contain_multiple_types(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        types_seen = {i["type"] for i in result["insights"]}
        assert len(types_seen) >= 2
        assert "quantitative_impact" in types_seen
        assert "risk_propagation" in types_seen

    def test_insights_contain_critical_severity(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        severities = {i["severity"] for i in result["insights"]}
        assert "critical" in severities

    def test_insight_text_variables_filled(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        for insight in result["insights"]:
            # No unfilled template variables
            assert "{" not in insight["text"] or "}" not in insight["text"].split("{")[-1]

    def test_updated_nodes_in_delta_graph(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        updated_ids = {n["id"] for n in result["delta_graph"]["updated_nodes"]}
        assert "E_ACQ_101" in updated_ids  # direct effect
        assert "C_ALPHA" in updated_ids    # ripple
        assert "C_BETA" in updated_ids     # ripple

    def test_highlight_edges_present(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        edges = result["delta_graph"]["highlight_edges"]
        assert len(edges) >= 1

    def test_action_not_found(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("nonexistent_action", "E_ACQ_101")
        assert result["status"] == "error"

    def test_action_without_ripple_rules(self, loaded_engine: OntologyEngine):
        result = loaded_engine.execute_action("trigger_acquisition_success", "E_ACQ_101")
        assert result["status"] == "success"
        assert loaded_engine.graph.nodes["E_ACQ_101"]["status"] == "COMPLETED"
        assert result["insights"] == []

    def test_recalculate_valuation_applied(self, loaded_engine: OntologyEngine):
        """R001 triggers recalculate_valuation on C_ALPHA (shock_factor=-0.3)."""
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        new_val = loaded_engine.graph.nodes["C_ALPHA"]["valuation"]
        assert new_val == pytest.approx(10000000 * 0.7)

    def test_risk_status_updated(self, loaded_engine: OntologyEngine):
        """R002 triggers update_risk_status on C_BETA."""
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        assert loaded_engine.graph.nodes["C_BETA"]["risk_status"] == "HIGH_RISK"

    def test_beta_valuation_adjusted(self, loaded_engine: OntologyEngine):
        """R003 triggers adjust_numeric on C_BETA (factor=0.8)."""
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        # R002 fires first (update_risk_status), then R003 (adjust_numeric with factor 0.8)
        # Both target C_BETA via TARGET_OF. Beta original valuation = 5000000
        new_val = loaded_engine.graph.nodes["C_BETA"]["valuation"]
        assert new_val == pytest.approx(5000000 * 0.8)


# ---------------------------------------------------------------------------
# Tests: reset
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_restores_node_attributes(self, loaded_engine: OntologyEngine):
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        # Verify mutation happened
        assert loaded_engine.graph.nodes["E_ACQ_101"]["status"] == "FAILED"

        loaded_engine.reset()

        assert loaded_engine.graph.nodes["E_ACQ_101"]["status"] == "PENDING"
        assert loaded_engine.graph.nodes["C_ALPHA"]["valuation"] == 10000000
        assert loaded_engine.graph.nodes["C_BETA"]["risk_status"] == "NORMAL"
        assert loaded_engine.graph.nodes["C_BETA"]["valuation"] == 5000000

    def test_reset_clears_accumulators(self, loaded_engine: OntologyEngine):
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        loaded_engine.reset()
        assert loaded_engine.insights_feed == []
        assert loaded_engine.ripple_path == []
        assert loaded_engine.updated_nodes == []
        assert loaded_engine.highlight_edges == []

    def test_execute_after_reset_gives_same_result(self, loaded_engine: OntologyEngine):
        result1 = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        loaded_engine.reset()
        result2 = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")

        assert result1["status"] == result2["status"]
        assert len(result1["ripple_path"]) == len(result2["ripple_path"])
        assert len(result1["insights"]) == len(result2["insights"])


# ---------------------------------------------------------------------------
# Tests: get_graph_for_render
# ---------------------------------------------------------------------------


class TestGetGraphForRender:
    def test_returns_nodes_and_edges(self, loaded_engine: OntologyEngine):
        data = loaded_engine.get_graph_for_render()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 4
        assert len(data["edges"]) == 4

    def test_node_includes_all_attrs(self, loaded_engine: OntologyEngine):
        data = loaded_engine.get_graph_for_render()
        alpha = next(n for n in data["nodes"] if n["id"] == "C_ALPHA")
        assert alpha["name"] == "Alpha Corp"
        assert alpha["type"] == "Company"
        assert alpha["valuation"] == 10000000


# ---------------------------------------------------------------------------
# Tests: get_available_actions
# ---------------------------------------------------------------------------


class TestGetAvailableActions:
    def test_all_actions_when_no_node(self, loaded_engine: OntologyEngine):
        actions = loaded_engine.get_available_actions()
        assert len(actions) == 2

    def test_filtered_by_node_type(self, loaded_engine: OntologyEngine):
        actions = loaded_engine.get_available_actions("E_ACQ_101")
        assert len(actions) == 2  # Both actions target Event_Acquisition
        ids = {a["action_id"] for a in actions}
        assert "trigger_acquisition_failure" in ids

    def test_no_actions_for_company(self, loaded_engine: OntologyEngine):
        actions = loaded_engine.get_available_actions("C_ALPHA")
        assert len(actions) == 0

    def test_unknown_node_returns_empty(self, loaded_engine: OntologyEngine):
        actions = loaded_engine.get_available_actions("NONEXISTENT")
        assert len(actions) == 0


# ---------------------------------------------------------------------------
# Tests: condition evaluation
# ---------------------------------------------------------------------------


class TestConditionEval:
    def test_true_condition(self, loaded_engine: OntologyEngine):
        result = loaded_engine._eval_condition(
            "target.get('risk_status') == 'NORMAL'",
            "E_ACQ_101",
            "C_ALPHA",
        )
        assert result is True

    def test_false_condition(self, loaded_engine: OntologyEngine):
        result = loaded_engine._eval_condition(
            "target.get('valuation', 0) > 99999999",
            "E_ACQ_101",
            "C_ALPHA",
        )
        assert result is False

    def test_invalid_condition_returns_false(self, loaded_engine: OntologyEngine):
        result = loaded_engine._eval_condition(
            "this is not valid python",
            "E_ACQ_101",
            "C_ALPHA",
        )
        assert result is False
