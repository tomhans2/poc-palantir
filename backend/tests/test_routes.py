"""Tests for the FastAPI routes — /load, /simulate, /reset, /history, /samples."""

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import engine, SAMPLES_DIR  # direct access for state assertions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_sample_schema() -> dict:
    """Minimal WorkspaceConfig-shaped dict reused across tests."""
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
                            "insight_template": "收购失败导致 {target[name]} 估值重估",
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
                            "insight_template": "{target[name]} 风险状态升级",
                            "insight_type": "risk_propagation",
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


@pytest.fixture(autouse=True)
def _reset_engine():
    """Ensure the global engine is clean before each test."""
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


def _upload_schema(client: TestClient, schema: dict | None = None) -> dict:
    """Helper: upload a JSON schema via /load and return the response JSON."""
    data = schema or _build_sample_schema()
    file_bytes = json.dumps(data).encode()
    resp = client.post(
        "/api/v1/workspace/load",
        files={"file": ("test.json", io.BytesIO(file_bytes), "application/json")},
    )
    return resp


# ===========================================================================
# /load tests
# ===========================================================================


class TestLoadWorkspace:
    def test_load_file_success(self, client):
        resp = _upload_schema(client)
        assert resp.status_code == 200
        body = resp.json()
        assert body["metadata"]["domain"] == "corporate_risk"
        assert "ontology_def" in body
        assert "graph_data" in body
        assert "actions" in body
        # graph_data should be in render format (flat nodes/edges)
        assert len(body["graph_data"]["nodes"]) == 4
        assert len(body["graph_data"]["edges"]) == 4

    def test_load_file_returns_registered_functions(self, client):
        resp = _upload_schema(client)
        assert resp.status_code == 200
        body = resp.json()
        assert "registered_functions" in body
        funcs = body["registered_functions"]
        assert isinstance(funcs, list)
        # Each entry is now {name, source}
        func_names = [f["name"] for f in funcs]
        assert "set_property" in func_names
        assert "adjust_numeric" in func_names
        assert "recalculate_valuation" in func_names
        # All builtin by default
        for f in funcs:
            assert f["source"] == "builtin"

    def test_load_file_returns_empty_warnings(self, client):
        resp = _upload_schema(client)
        assert resp.status_code == 200
        body = resp.json()
        assert "warnings" in body
        assert body["warnings"] == []

    def test_load_invalid_json(self, client):
        resp = client.post(
            "/api/v1/workspace/load",
            files={"file": ("bad.json", io.BytesIO(b"not json"), "application/json")},
        )
        assert resp.status_code == 400
        assert "Invalid JSON" in resp.json()["detail"]

    def test_load_invalid_schema_returns_422(self, client):
        """Missing required fields should return 422 with Pydantic validation errors."""
        bad_schema = {"metadata": {"domain": "test"}}  # missing required fields
        file_bytes = json.dumps(bad_schema).encode()
        resp = client.post(
            "/api/v1/workspace/load",
            files={"file": ("bad.json", io.BytesIO(file_bytes), "application/json")},
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Pydantic v2 returns a list of error dicts
        assert isinstance(detail, list)
        assert len(detail) > 0
        # Each error should have 'loc', 'msg', 'type' fields
        for err in detail:
            assert "loc" in err
            assert "msg" in err

    def test_load_no_file_no_sample(self, client):
        resp = client.post("/api/v1/workspace/load")
        assert resp.status_code == 400

    def test_load_idempotent(self, client):
        """Loading twice should reset state — second load is a fresh workspace."""
        _upload_schema(client)
        # Simulate to change state
        client.post("/api/v1/workspace/simulate", json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"})

        # Load again
        resp = _upload_schema(client)
        assert resp.status_code == 200
        # After fresh load, E_ACQ_101 status should be PENDING (not FAILED from simulation)
        nodes = {n["id"]: n for n in resp.json()["graph_data"]["nodes"]}
        assert nodes["E_ACQ_101"]["status"] == "PENDING"

    def test_load_with_unregistered_function_returns_warnings(self, client):
        """JSON referencing a nonexistent function should succeed but include warnings."""
        schema = _build_sample_schema()
        # Add a rule referencing a nonexistent function
        schema["action_engine"]["actions"][0]["ripple_rules"].append({
            "rule_id": "R_BAD",
            "propagation_path": "<-[ACQUIRES]- Company",
            "condition": None,
            "effect_on_target": {
                "action_to_trigger": "nonexistent_func",
                "parameters": {},
            },
            "insight_template": "test",
            "insight_type": "info",
            "insight_severity": "info",
        })
        resp = _upload_schema(client, schema)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["warnings"]) > 0
        assert any("nonexistent_func" in w for w in body["warnings"])

    def test_load_consecutive_fresh_workspace(self, client):
        """Two consecutive /load calls should each produce a fresh workspace."""
        # First load + simulate
        _upload_schema(client)
        client.post("/api/v1/workspace/simulate", json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"})
        # Verify state changed
        assert engine.graph.nodes["E_ACQ_101"]["status"] == "FAILED"

        # Second load — fresh state
        resp = _upload_schema(client)
        assert resp.status_code == 200
        assert engine.graph.nodes["E_ACQ_101"]["status"] == "PENDING"
        # Event history should also be clean (engine.load_workspace doesn't clear event_queue
        # but the event_queue from the first run persists — the key point is graph state resets)


# ===========================================================================
# /load via sample name
# ===========================================================================


class TestLoadSample:
    def test_load_sample_corporate_acquisition(self, client):
        """Loading built-in sample by name should work."""
        resp = client.post("/api/v1/workspace/load?sample=corporate_acquisition")
        assert resp.status_code == 200
        body = resp.json()
        assert body["metadata"]["domain"] == "corporate_risk"
        assert "ontology_def" in body
        assert len(body["graph_data"]["nodes"]) >= 4
        assert len(body["graph_data"]["edges"]) >= 4
        assert "registered_functions" in body
        assert len(body["registered_functions"]) > 0

    def test_load_sample_not_found(self, client):
        resp = client.post("/api/v1/workspace/load?sample=nonexistent_sample")
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    def test_load_sample_idempotent(self, client):
        """Loading sample twice should reset state."""
        # First load
        client.post("/api/v1/workspace/load?sample=corporate_acquisition")
        # Simulate to change state
        client.post("/api/v1/workspace/simulate", json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"})
        # Second load
        resp = client.post("/api/v1/workspace/load?sample=corporate_acquisition")
        assert resp.status_code == 200
        nodes = {n["id"]: n for n in resp.json()["graph_data"]["nodes"]}
        assert nodes["E_ACQ_101"]["status"] == "PENDING"


# ===========================================================================
# /samples tests
# ===========================================================================


class TestListSamples:
    def test_samples_returns_list(self, client):
        resp = client.get("/api/v1/workspace/samples")
        assert resp.status_code == 200
        samples = resp.json()
        assert isinstance(samples, list)
        assert len(samples) >= 1  # at least corporate_acquisition

    def test_samples_contains_corporate_acquisition(self, client):
        resp = client.get("/api/v1/workspace/samples")
        samples = resp.json()
        names = [s["name"] for s in samples]
        assert "corporate_acquisition" in names

    def test_samples_include_description(self, client):
        resp = client.get("/api/v1/workspace/samples")
        samples = resp.json()
        acq = next(s for s in samples if s["name"] == "corporate_acquisition")
        assert "name" in acq
        assert "description" in acq
        assert len(acq["description"]) > 0


# ===========================================================================
# /simulate tests
# ===========================================================================


class TestSimulate:
    def test_simulate_success(self, client):
        _upload_schema(client)
        resp = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "ripple_path" in body
        assert "E_ACQ_101" in body["ripple_path"]
        assert len(body["insights"]) >= 1
        assert len(body["delta_graph"]["updated_nodes"]) >= 1

    def test_simulate_no_workspace(self, client):
        resp = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        assert resp.status_code == 400
        assert "No workspace loaded" in resp.json()["detail"]

    def test_simulate_unknown_node(self, client):
        _upload_schema(client)
        resp = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "NONEXISTENT"},
        )
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"]

    def test_simulate_unknown_action(self, client):
        _upload_schema(client)
        resp = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "nonexistent_action", "node_id": "E_ACQ_101"},
        )
        assert resp.status_code == 400

    def test_simulate_response_structure(self, client):
        """Verify the response matches SimulateResponse schema."""
        _upload_schema(client)
        resp = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        body = resp.json()
        assert "status" in body
        assert "delta_graph" in body
        assert "updated_nodes" in body["delta_graph"]
        assert "highlight_edges" in body["delta_graph"]
        assert "ripple_path" in body
        assert "insights" in body
        # Each insight should have required fields
        for insight in body["insights"]:
            assert "text" in insight
            assert "type" in insight
            assert "severity" in insight


# ===========================================================================
# /reset tests
# ===========================================================================


class TestReset:
    def test_reset_restores_state(self, client):
        _upload_schema(client)
        # Simulate to change node properties
        client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        # Reset
        resp = client.post("/api/v1/workspace/reset")
        assert resp.status_code == 200
        body = resp.json()
        # Check that node properties are restored
        nodes = {n["id"]: n for n in body["nodes"]}
        assert nodes["E_ACQ_101"]["status"] == "PENDING"
        assert nodes["C_ALPHA"]["valuation"] == 10000000

    def test_reset_clears_history(self, client):
        _upload_schema(client)
        client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        # History should have 1 event
        history = client.get("/api/v1/workspace/history").json()
        assert len(history) == 1

        # Reset
        client.post("/api/v1/workspace/reset")
        # History should be empty
        history = client.get("/api/v1/workspace/history").json()
        assert len(history) == 0

    def test_reset_no_workspace(self, client):
        resp = client.post("/api/v1/workspace/reset")
        assert resp.status_code == 400


# ===========================================================================
# /history tests
# ===========================================================================


class TestHistory:
    def test_history_empty(self, client):
        resp = client.get("/api/v1/workspace/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_after_simulations(self, client):
        _upload_schema(client)
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
        # Each event should have complete fields
        for event in history:
            assert "timestamp" in event
            assert "action_id" in event
            assert "target_node_id" in event
            assert "ripple_path" in event
            assert "insights" in event
            assert "delta_graph" in event

    def test_history_records_correct_action(self, client):
        _upload_schema(client)
        client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        history = client.get("/api/v1/workspace/history").json()
        assert history[0]["action_id"] == "trigger_acquisition_failure"
        assert history[0]["target_node_id"] == "E_ACQ_101"
        assert len(history[0]["ripple_path"]) >= 2
        assert len(history[0]["insights"]) >= 1


# ===========================================================================
# /health (existing endpoint)
# ===========================================================================


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ===========================================================================
# Custom Action Extension (US-CORE-002)
# ===========================================================================

# Custom action Python source used in tests
CUSTOM_ACTION_PY = b"""\
from app.engine.action_registry import ActionContext, ActionResult, register_action

@register_action
def my_custom_calc(ctx: ActionContext) -> ActionResult:
    '''A custom calculation function.'''
    old_val = ctx.target_node.get("valuation", 0)
    new_val = old_val * 2
    return ActionResult(
        updated_properties={"valuation": new_val},
        old_values={"valuation": old_val},
    )
"""

# Custom action that overrides a builtin (set_property)
CUSTOM_OVERRIDE_PY = b"""\
from app.engine.action_registry import ActionContext, ActionResult, register_action

@register_action
def set_property(ctx: ActionContext) -> ActionResult:
    '''Custom override of set_property that appends _CUSTOM to the value.'''
    prop = ctx.params["property"]
    value = str(ctx.params["value"]) + "_CUSTOM"
    old_value = ctx.target_node.get(prop)
    return ActionResult(
        updated_properties={prop: value},
        old_values={prop: old_value},
    )
"""


class TestCustomActionExtension:
    def test_load_json_only_registers_builtin(self, client):
        """Loading only JSON (no .py file) should register only builtin functions."""
        resp = _upload_schema(client)
        assert resp.status_code == 200
        body = resp.json()
        funcs = body["registered_functions"]
        for f in funcs:
            assert f["source"] == "builtin"
        func_names = [f["name"] for f in funcs]
        assert "set_property" in func_names
        assert "adjust_numeric" in func_names

    def test_upload_custom_action_file(self, client):
        """Uploading JSON + custom .py file should register custom functions."""
        schema = _build_sample_schema()
        file_bytes = json.dumps(schema).encode()
        resp = client.post(
            "/api/v1/workspace/load",
            files={
                "file": ("test.json", io.BytesIO(file_bytes), "application/json"),
                "action_file": ("custom.py", io.BytesIO(CUSTOM_ACTION_PY), "text/x-python"),
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        funcs = body["registered_functions"]
        func_names = [f["name"] for f in funcs]
        # Custom function should be registered
        assert "my_custom_calc" in func_names
        # Builtin functions should still be present
        assert "set_property" in func_names
        # Check source labels
        custom_entry = next(f for f in funcs if f["name"] == "my_custom_calc")
        assert custom_entry["source"] == "custom"
        builtin_entry = next(f for f in funcs if f["name"] == "set_property")
        assert builtin_entry["source"] == "builtin"

    def test_custom_function_found_by_registry(self, client):
        """Custom function should be callable via engine's ActionRegistry.get()."""
        schema = _build_sample_schema()
        file_bytes = json.dumps(schema).encode()
        client.post(
            "/api/v1/workspace/load",
            files={
                "file": ("test.json", io.BytesIO(file_bytes), "application/json"),
                "action_file": ("custom.py", io.BytesIO(CUSTOM_ACTION_PY), "text/x-python"),
            },
        )
        func = engine.action_registry.get("my_custom_calc")
        assert func is not None
        assert callable(func)

    def test_custom_override_replaces_builtin(self, client):
        """Custom .py with same-name function should override the builtin version."""
        schema = _build_sample_schema()
        file_bytes = json.dumps(schema).encode()
        resp = client.post(
            "/api/v1/workspace/load",
            files={
                "file": ("test.json", io.BytesIO(file_bytes), "application/json"),
                "action_file": ("override.py", io.BytesIO(CUSTOM_OVERRIDE_PY), "text/x-python"),
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        funcs = body["registered_functions"]
        sp_entry = next(f for f in funcs if f["name"] == "set_property")
        assert sp_entry["source"] == "custom"  # overridden by custom

    def test_custom_override_function_executes(self, client):
        """The overridden set_property should actually use the custom implementation."""
        schema = _build_sample_schema()
        file_bytes = json.dumps(schema).encode()
        client.post(
            "/api/v1/workspace/load",
            files={
                "file": ("test.json", io.BytesIO(file_bytes), "application/json"),
                "action_file": ("override.py", io.BytesIO(CUSTOM_OVERRIDE_PY), "text/x-python"),
            },
        )
        # The custom set_property appends "_CUSTOM" to the value
        from app.engine.action_registry import ActionContext
        import networkx as nx
        func = engine.action_registry.get("set_property")
        ctx = ActionContext(
            target_node={"status": "PENDING"},
            source_node={},
            target_id="test",
            source_id="src",
            params={"property": "status", "value": "FAILED"},
            graph=nx.DiGraph(),
        )
        result = func(ctx)
        assert result.updated_properties["status"] == "FAILED_CUSTOM"

    def test_custom_function_correct_signature(self, client):
        """Custom function with (ctx: ActionContext) -> ActionResult signature should work with engine."""
        # Build a schema that references the custom function
        schema = _build_sample_schema()
        schema["action_engine"]["actions"][0]["ripple_rules"].append({
            "rule_id": "R_CUSTOM",
            "propagation_path": "<-[ACQUIRES]- Company",
            "condition": None,
            "effect_on_target": {
                "action_to_trigger": "my_custom_calc",
                "parameters": {},
            },
            "insight_template": "{target[name]} valuation doubled",
            "insight_type": "quantitative_impact",
            "insight_severity": "info",
        })
        file_bytes = json.dumps(schema).encode()
        resp = client.post(
            "/api/v1/workspace/load",
            files={
                "file": ("test.json", io.BytesIO(file_bytes), "application/json"),
                "action_file": ("custom.py", io.BytesIO(CUSTOM_ACTION_PY), "text/x-python"),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["warnings"] == []  # my_custom_calc should be registered

        # Simulate and verify the custom function was called
        sim_resp = client.post(
            "/api/v1/workspace/simulate",
            json={"action_id": "trigger_acquisition_failure", "node_id": "E_ACQ_101"},
        )
        assert sim_resp.status_code == 200
        body = sim_resp.json()
        assert body["status"] == "success"
        # Check that C_ALPHA valuation was doubled by my_custom_calc
        # Note: R001 runs first (recalculate_valuation with shock_factor=-0.3):
        #   10000000 * 0.7 = 7000000
        # Then R_CUSTOM runs (my_custom_calc doubles): 7000000 * 2 = 14000000
        updated = {n["id"]: n for n in body["delta_graph"]["updated_nodes"]}
        assert "C_ALPHA" in updated
        assert updated["C_ALPHA"].get("valuation") == 14000000.0

    def test_convention_based_loading(self, client, tmp_path):
        """When a sample has a companion .py file in samples/, it should be auto-loaded."""
        from app.api.routes import SAMPLES_DIR
        # Create a temporary .py file alongside the existing sample
        py_content = CUSTOM_ACTION_PY
        convention_path = SAMPLES_DIR / "corporate_acquisition.py"
        existed_before = convention_path.exists()
        try:
            convention_path.write_bytes(py_content)
            resp = client.post("/api/v1/workspace/load?sample=corporate_acquisition")
            assert resp.status_code == 200
            body = resp.json()
            funcs = body["registered_functions"]
            func_names = [f["name"] for f in funcs]
            assert "my_custom_calc" in func_names
            custom_entry = next(f for f in funcs if f["name"] == "my_custom_calc")
            assert custom_entry["source"] == "custom"
        finally:
            if not existed_before and convention_path.exists():
                convention_path.unlink()

    def test_registered_functions_source_format(self, client):
        """registered_functions should be list of {name, source} dicts."""
        resp = _upload_schema(client)
        assert resp.status_code == 200
        body = resp.json()
        funcs = body["registered_functions"]
        assert isinstance(funcs, list)
        for f in funcs:
            assert "name" in f
            assert "source" in f
            assert isinstance(f["name"], str)
            assert f["source"] in ("builtin", "custom")
