"""US-BE-007 — Backend engine end-to-end integration verification.

Validates the complete pipeline from JSON loading to ripple propagation,
ensuring all three intelligence layers (L1/L2/L3) and structured insights
work correctly. Also verifies all 4 API endpoints via FastAPI TestClient.
"""

import io
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.actions import action_functions
from app.api.routes import engine
from app.engine.graph_engine import OntologyEngine
from app.main import app
from app.models.workspace import WorkspaceConfig

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "samples" / "corporate_acquisition.json"


@pytest.fixture
def sample_data():
    with open(SAMPLE_PATH) as f:
        return json.load(f)


@pytest.fixture
def loaded_engine(sample_data):
    eng = OntologyEngine()
    eng.load_workspace(sample_data, action_module=action_functions)
    return eng


@pytest.fixture(autouse=True)
def _reset_global_engine():
    """Ensure the global engine singleton is clean before each test."""
    engine.graph.clear()
    engine.schema = None
    engine.initial_snapshot = {}
    engine.action_registry.__init__()
    engine.event_queue.clear()
    engine.insights_feed = []
    engine.ripple_path = []
    engine.updated_nodes = []
    engine.highlight_edges = []
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Full engine-level pipeline: load → execute → check → reset → re-execute
# ---------------------------------------------------------------------------


class TestEngineFullPipeline:
    """End-to-end validation at the engine level (no HTTP)."""

    def test_graph_node_count_matches_json(self, loaded_engine, sample_data):
        expected = len(sample_data["graph_data"]["nodes"])
        assert loaded_engine.graph.number_of_nodes() == expected

    def test_graph_edge_count_matches_json(self, loaded_engine, sample_data):
        expected = len(sample_data["graph_data"]["edges"])
        assert loaded_engine.graph.number_of_edges() == expected

    def test_execute_returns_success(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        assert result["status"] == "success"

    def test_updated_nodes_include_direct_target(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        updated_ids = {n["id"] for n in result["delta_graph"]["updated_nodes"]}
        assert "E_ACQ_101" in updated_ids

    def test_updated_nodes_include_ripple_affected(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        updated_ids = {n["id"] for n in result["delta_graph"]["updated_nodes"]}
        # Ripple rules propagate to companies connected via ACQUIRES and TARGET_OF
        assert len(updated_ids) >= 2  # at least target + 1 ripple node

    def test_highlight_edges_on_propagation_path(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        edges = result["delta_graph"]["highlight_edges"]
        assert len(edges) >= 1
        # Each highlighted edge should have source, target, type
        for edge in edges:
            assert "source" in edge
            assert "target" in edge
            assert "type" in edge

    def test_insights_have_at_least_3_types(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        insight_types = {i["type"] for i in result["insights"]}
        assert len(insight_types) >= 3, f"Got only {insight_types}"

    def test_insights_include_critical_severity(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        severities = {i["severity"] for i in result["insights"]}
        assert "critical" in severities

    def test_insight_text_has_no_unfilled_placeholders(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        for insight in result["insights"]:
            text = insight["text"]
            assert "{target[" not in text, f"Unfilled placeholder in: {text}"
            assert "{source[" not in text, f"Unfilled placeholder in: {text}"
            # Also check for generic Python format braces like {name}
            # (but allow normal text with curly braces)
            unfilled = re.findall(r"\{[a-z_]+\[", text)
            assert len(unfilled) == 0, f"Unfilled template in: {text}"

    def test_insights_are_structured_objects(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        for insight in result["insights"]:
            assert "text" in insight
            assert "type" in insight
            assert "severity" in insight
            assert "source_node" in insight
            assert "target_node" in insight
            assert "rule_id" in insight

    def test_ripple_path_includes_source_and_affected(self, loaded_engine):
        result = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        assert "E_ACQ_101" in result["ripple_path"]
        assert len(result["ripple_path"]) >= 3  # source + at least 2 affected

    def test_reset_restores_initial_state(self, loaded_engine):
        """After reset, all node properties should return to their initial values."""
        # Capture initial state
        initial_acq_status = loaded_engine.graph.nodes["E_ACQ_101"]["status"]
        initial_alpha_valuation = loaded_engine.graph.nodes["C_ALPHA"]["valuation"]
        initial_alpha_risk = loaded_engine.graph.nodes["C_ALPHA"]["risk_status"]
        initial_beta_risk = loaded_engine.graph.nodes["C_BETA"]["risk_status"]

        # Execute action that changes state
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")

        # Verify state changed
        assert loaded_engine.graph.nodes["E_ACQ_101"]["status"] != initial_acq_status

        # Reset
        loaded_engine.reset()

        # Verify initial state restored
        assert loaded_engine.graph.nodes["E_ACQ_101"]["status"] == initial_acq_status
        assert loaded_engine.graph.nodes["C_ALPHA"]["valuation"] == initial_alpha_valuation
        assert loaded_engine.graph.nodes["C_ALPHA"]["risk_status"] == initial_alpha_risk
        assert loaded_engine.graph.nodes["C_BETA"]["risk_status"] == initial_beta_risk

    def test_re_execute_after_reset_gives_consistent_results(self, loaded_engine):
        """Running the same action after reset should produce the same results."""
        # First execution
        result_1 = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        insights_1_types = sorted(i["type"] for i in result_1["insights"])
        ripple_1 = sorted(result_1["ripple_path"])
        updated_1_ids = sorted(n["id"] for n in result_1["delta_graph"]["updated_nodes"])

        # Reset
        loaded_engine.reset()

        # Second execution
        result_2 = loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        insights_2_types = sorted(i["type"] for i in result_2["insights"])
        ripple_2 = sorted(result_2["ripple_path"])
        updated_2_ids = sorted(n["id"] for n in result_2["delta_graph"]["updated_nodes"])

        assert result_2["status"] == result_1["status"]
        assert ripple_2 == ripple_1
        assert insights_2_types == insights_1_types
        assert updated_2_ids == updated_1_ids

    def test_action_registry_contains_all_functions(self, loaded_engine):
        registered = loaded_engine.action_registry.list_actions()
        expected = [
            "adjust_numeric",
            "compute_margin_gap",
            "graph_weighted_exposure",
            "recalculate_valuation",
            "set_property",
            "update_risk_status",
        ]
        assert registered == expected

    def test_event_queue_records_execution(self, loaded_engine):
        """Event queue should record each successful action execution."""
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        history = loaded_engine.event_queue.get_history()
        assert len(history) == 1
        assert history[0]["action_id"] == "trigger_acquisition_failure"
        assert history[0]["target_node_id"] == "E_ACQ_101"
        assert len(history[0]["ripple_path"]) >= 3
        assert len(history[0]["insights"]) >= 3

    def test_two_simulations_produce_two_history_events(self, loaded_engine):
        loaded_engine.execute_action("trigger_acquisition_failure", "E_ACQ_101")
        loaded_engine.execute_action("trigger_acquisition_success", "E_ACQ_101")
        history = loaded_engine.event_queue.get_history()
        assert len(history) == 2
        assert history[0]["action_id"] == "trigger_acquisition_failure"
        assert history[1]["action_id"] == "trigger_acquisition_success"


# ---------------------------------------------------------------------------
# API-level end-to-end: all 4 endpoints callable via TestClient
# ---------------------------------------------------------------------------


class TestAPIEndToEnd:
    """Verify all 4 API endpoints work correctly through the full pipeline."""

    def _load_sample(self, client: TestClient) -> dict:
        resp = client.post("/api/v1/workspace/load?sample=corporate_acquisition")
        assert resp.status_code == 200
        return resp.json()

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_load_sample_via_api(self, client):
        body = self._load_sample(client)
        assert body["metadata"]["domain"] == "corporate_risk"
        assert "ontology_def" in body
        assert "graph_data" in body
        assert "actions" in body
        assert "registered_functions" in body
        assert len(body["graph_data"]["nodes"]) >= 6

    def test_load_file_upload_via_api(self, client):
        with open(SAMPLE_PATH) as f:
            data = json.load(f)
        file_bytes = json.dumps(data).encode()
        resp = client.post(
            "/api/v1/workspace/load",
            files={"file": ("test.json", io.BytesIO(file_bytes), "application/json")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["metadata"]["domain"] == "corporate_risk"
        assert len(body["graph_data"]["nodes"]) >= 6

    def test_simulate_via_api(self, client):
        self._load_sample(client)
        resp = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "ripple_path" in body
        assert "E_ACQ_101" in body["ripple_path"]
        assert len(body["ripple_path"]) >= 3
        assert len(body["insights"]) >= 3
        # Verify insight structure
        for insight in body["insights"]:
            assert "text" in insight
            assert "type" in insight
            assert "severity" in insight
        # Verify delta_graph
        assert len(body["delta_graph"]["updated_nodes"]) >= 2
        assert len(body["delta_graph"]["highlight_edges"]) >= 1

    def test_simulate_response_insight_types(self, client):
        self._load_sample(client)
        resp = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        body = resp.json()
        insight_types = {i["type"] for i in body["insights"]}
        assert len(insight_types) >= 3
        severities = {i["severity"] for i in body["insights"]}
        assert "critical" in severities

    def test_reset_via_api(self, client):
        self._load_sample(client)
        # Simulate to change state
        client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        # Reset
        resp = client.post("/api/v1/workspace/reset")
        assert resp.status_code == 200
        body = resp.json()
        nodes = {n["id"]: n for n in body["nodes"]}
        assert nodes["E_ACQ_101"]["status"] == "PENDING"
        assert nodes["C_ALPHA"]["valuation"] == 10000000
        assert nodes["C_ALPHA"]["risk_status"] == "NORMAL"

    def test_history_via_api(self, client):
        self._load_sample(client)
        # Run two simulations
        client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_success", "node_id": "E_ACQ_101"},
        )
        resp = client.get("/api/v1/workspace/history")
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 2
        for event in history:
            assert "timestamp" in event
            assert "action_id" in event
            assert "target_node_id" in event
            assert "ripple_path" in event
            assert "insights" in event
            assert "delta_graph" in event

    def test_samples_endpoint(self, client):
        resp = client.get("/api/v1/workspace/samples")
        assert resp.status_code == 200
        samples = resp.json()
        assert isinstance(samples, list)
        assert len(samples) >= 1
        names = [s["name"] for s in samples]
        assert "corporate_acquisition" in names

    def test_full_api_round_trip(self, client):
        """Complete round trip: load → simulate → verify → reset → simulate again → verify consistency."""
        # Load
        load_body = self._load_sample(client)
        assert load_body["metadata"]["domain"] == "corporate_risk"

        # Simulate #1
        sim1 = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        ).json()
        assert sim1["status"] == "success"
        sim1_types = sorted(i["type"] for i in sim1["insights"])
        sim1_path = sorted(sim1["ripple_path"])

        # Verify history has 1 event
        history = client.get("/api/v1/workspace/history").json()
        assert len(history) == 1

        # Reset
        reset_body = client.post("/api/v1/workspace/reset").json()
        nodes = {n["id"]: n for n in reset_body["nodes"]}
        assert nodes["E_ACQ_101"]["status"] == "PENDING"

        # History cleared
        history = client.get("/api/v1/workspace/history").json()
        assert len(history) == 0

        # Simulate #2 (same action — should give same results)
        sim2 = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        ).json()
        assert sim2["status"] == "success"
        sim2_types = sorted(i["type"] for i in sim2["insights"])
        sim2_path = sorted(sim2["ripple_path"])

        assert sim2_types == sim1_types
        assert sim2_path == sim1_path
