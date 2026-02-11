"""Tests for US-DATA-001 — corporate_acquisition.json sample data validation.

Verifies the sample JSON file meets all acceptance criteria:
node/edge counts, insight types/severities, ripple path length, and L1/L2/L3 coverage.
"""

import json
from pathlib import Path

import pytest

from app.engine.graph_engine import OntologyEngine
from app.models.workspace import WorkspaceConfig
import app.actions.action_functions as action_functions


SAMPLE_PATH = Path(__file__).resolve().parent.parent / "samples" / "corporate_acquisition.json"


@pytest.fixture
def sample_data():
    """Load and return the raw sample JSON dict."""
    with open(SAMPLE_PATH) as f:
        return json.load(f)


@pytest.fixture
def loaded_engine(sample_data):
    """Load the sample data into an OntologyEngine with real action functions."""
    eng = OntologyEngine()
    eng.load_workspace(sample_data, action_module=action_functions)
    return eng


# ---------------------------------------------------------------------------
# Schema / structure validation
# ---------------------------------------------------------------------------


class TestSampleStructure:
    def test_pydantic_validation(self, sample_data):
        """JSON parses into a valid WorkspaceConfig without errors."""
        config = WorkspaceConfig(**sample_data)
        assert config.metadata.domain == "corporate_risk"

    def test_metadata(self, sample_data):
        meta = sample_data["metadata"]
        assert "domain" in meta
        assert "version" in meta
        assert "description" in meta

    def test_node_types_include_company_and_event(self, sample_data):
        nt = sample_data["ontology_def"]["node_types"]
        assert "Company" in nt
        assert "Event_Acquisition" in nt
        # Company: blue circle
        assert nt["Company"]["color"] == "#4A90D9"
        assert nt["Company"]["shape"] == "circle"
        # Event_Acquisition: orange diamond
        assert nt["Event_Acquisition"]["color"] == "#F5A623"
        assert nt["Event_Acquisition"]["shape"] == "diamond"

    def test_node_types_include_person(self, sample_data):
        nt = sample_data["ontology_def"]["node_types"]
        assert "Person" in nt

    def test_edge_types_include_required(self, sample_data):
        et = sample_data["ontology_def"]["edge_types"]
        assert "ACQUIRES" in et
        assert "TARGET_OF" in et
        assert "SUPPLIES_TO" in et

    def test_node_count(self, sample_data):
        """6-10 nodes."""
        nodes = sample_data["graph_data"]["nodes"]
        assert 6 <= len(nodes) <= 10

    def test_node_type_distribution(self, sample_data):
        """3-4 Companies + 1-2 Event_Acquisition + optional Person."""
        nodes = sample_data["graph_data"]["nodes"]
        types = [n["type"] for n in nodes]
        assert 3 <= types.count("Company") <= 4
        assert 1 <= types.count("Event_Acquisition") <= 2

    def test_edges_form_meaningful_topology(self, sample_data):
        """Edges include ACQUIRES, TARGET_OF, and SUPPLIES_TO with dependency_weight."""
        edges = sample_data["graph_data"]["edges"]
        edge_types = {e["type"] for e in edges}
        assert "ACQUIRES" in edge_types
        assert "TARGET_OF" in edge_types
        assert "SUPPLIES_TO" in edge_types
        # At least one SUPPLIES_TO edge has dependency_weight
        supply_edges = [e for e in edges if e["type"] == "SUPPLIES_TO"]
        assert any("dependency_weight" in e.get("properties", {}) for e in supply_edges)

    def test_action_engine_has_two_actions(self, sample_data):
        actions = sample_data["action_engine"]["actions"]
        assert len(actions) >= 2
        ids = {a["action_id"] for a in actions}
        assert "trigger_acquisition_failure" in ids
        assert "trigger_acquisition_success" in ids

    def test_failure_action_has_3_to_5_ripple_rules(self, sample_data):
        actions = sample_data["action_engine"]["actions"]
        failure = next(a for a in actions if a["action_id"] == "trigger_acquisition_failure")
        rules = failure["ripple_rules"]
        assert 3 <= len(rules) <= 5

    def test_ripple_rules_cover_l1_l2_l3(self, sample_data):
        """Rules should reference L1 (set_property/adjust_numeric), L2 (recalculate_valuation), L3 (graph_weighted_exposure)."""
        actions = sample_data["action_engine"]["actions"]
        failure = next(a for a in actions if a["action_id"] == "trigger_acquisition_failure")
        triggered_funcs = {r["effect_on_target"]["action_to_trigger"] for r in failure["ripple_rules"]}
        # L1
        assert "set_property" in triggered_funcs or "adjust_numeric" in triggered_funcs or "update_risk_status" in triggered_funcs
        # L2
        assert "recalculate_valuation" in triggered_funcs
        # L3
        assert "graph_weighted_exposure" in triggered_funcs

    def test_ripple_rules_have_insight_metadata(self, sample_data):
        """Each rule has insight_type and insight_severity."""
        actions = sample_data["action_engine"]["actions"]
        failure = next(a for a in actions if a["action_id"] == "trigger_acquisition_failure")
        for rule in failure["ripple_rules"]:
            assert "insight_type" in rule and rule["insight_type"]
            assert "insight_severity" in rule and rule["insight_severity"]

    def test_insight_types_variety(self, sample_data):
        """Rules cover multiple insight types."""
        actions = sample_data["action_engine"]["actions"]
        failure = next(a for a in actions if a["action_id"] == "trigger_acquisition_failure")
        types = {r["insight_type"] for r in failure["ripple_rules"]}
        # Should have at least 3 different types
        assert len(types) >= 3

    def test_insight_templates_use_format_map(self, sample_data):
        """insight_template uses {source[xxx]} or {target[xxx]} syntax."""
        actions = sample_data["action_engine"]["actions"]
        failure = next(a for a in actions if a["action_id"] == "trigger_acquisition_failure")
        for rule in failure["ripple_rules"]:
            template = rule.get("insight_template", "")
            assert "{target[" in template or "{source[" in template


# ---------------------------------------------------------------------------
# Engine loading validation
# ---------------------------------------------------------------------------


class TestSampleEngineLoading:
    def test_graph_node_count(self, loaded_engine):
        assert loaded_engine.graph.number_of_nodes() == 8

    def test_graph_edge_count(self, loaded_engine):
        assert loaded_engine.graph.number_of_edges() == 10

    def test_core_nodes_present(self, loaded_engine):
        assert loaded_engine.graph.has_node("C_ALPHA")
        assert loaded_engine.graph.has_node("C_BETA")
        assert loaded_engine.graph.has_node("C_GAMMA")
        assert loaded_engine.graph.has_node("E_ACQ_101")


# ---------------------------------------------------------------------------
# Execute action validation
# ---------------------------------------------------------------------------


class TestSampleExecuteAction:
    def test_failure_returns_success(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        assert result["status"] == "success"

    def test_failure_returns_at_least_3_insights(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        assert len(result["insights"]) >= 3

    def test_failure_insights_have_multiple_types(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        types = {i["type"] for i in result["insights"]}
        assert len(types) >= 3

    def test_failure_insights_have_critical_severity(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        severities = {i["severity"] for i in result["insights"]}
        assert "critical" in severities

    def test_failure_insight_text_filled(self, loaded_engine):
        """No unfilled template variables in insight text."""
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        for insight in result["insights"]:
            # Ensure no {xxx} placeholders remain
            text = insight["text"]
            assert "{target[" not in text
            assert "{source[" not in text

    def test_failure_ripple_path_length(self, loaded_engine):
        """ripple_path >= 3 (source + at least 2 affected nodes)."""
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        assert len(result["ripple_path"]) >= 3
        assert "E_ACQ_101" in result["ripple_path"]

    def test_failure_updated_nodes_include_affected(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        updated_ids = {n["id"] for n in result["delta_graph"]["updated_nodes"]}
        assert "E_ACQ_101" in updated_ids
        assert "C_ALPHA" in updated_ids

    def test_failure_highlight_edges_on_path(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        edges = result["delta_graph"]["highlight_edges"]
        assert len(edges) >= 1

    def test_reset_restores_all(self, loaded_engine):
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        loaded_engine.reset()
        assert loaded_engine.graph.nodes["E_ACQ_101"]["status"] == "PENDING"
        assert loaded_engine.graph.nodes["C_ALPHA"]["valuation"] == 10000000
        assert loaded_engine.graph.nodes["C_ALPHA"]["risk_status"] == "NORMAL"
        assert loaded_engine.graph.nodes["C_BETA"]["risk_status"] == "NORMAL"
