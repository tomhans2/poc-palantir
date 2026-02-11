"""Tests for EventQueue — simulation event recording and history retrieval."""

from datetime import datetime

import pytest

from app.engine.event_queue import EventQueue, SimulationEvent


# ---------------------------------------------------------------------------
# SimulationEvent dataclass
# ---------------------------------------------------------------------------


class TestSimulationEvent:
    def test_fields(self):
        event = SimulationEvent(
            timestamp="2024-01-15T12:00:00+00:00",
            action_id="test_action",
            target_node_id="N1",
            ripple_path=["N1", "N2"],
            insights=[{"text": "insight"}],
            delta_graph={"updated_nodes": []},
        )
        assert event.timestamp == "2024-01-15T12:00:00+00:00"
        assert event.action_id == "test_action"
        assert event.target_node_id == "N1"
        assert event.ripple_path == ["N1", "N2"]
        assert event.insights == [{"text": "insight"}]
        assert event.delta_graph == {"updated_nodes": []}


# ---------------------------------------------------------------------------
# EventQueue
# ---------------------------------------------------------------------------


class TestEventQueue:
    def test_empty_history(self):
        eq = EventQueue()
        assert eq.get_history() == []

    def test_push_and_get_history(self):
        eq = EventQueue()
        result = {
            "status": "success",
            "ripple_path": ["E_ACQ_101", "C_ALPHA"],
            "insights": [{"text": "Acquisition failed", "type": "event_trigger", "severity": "critical"}],
            "delta_graph": {
                "updated_nodes": [{"id": "E_ACQ_101", "status": "FAILED"}],
                "highlight_edges": [],
            },
        }
        eq.push("trigger_acquisition_failure", "E_ACQ_101", result)

        history = eq.get_history()
        assert len(history) == 1
        event = history[0]
        assert event["action_id"] == "trigger_acquisition_failure"
        assert event["target_node_id"] == "E_ACQ_101"
        assert event["ripple_path"] == ["E_ACQ_101", "C_ALPHA"]
        assert len(event["insights"]) == 1
        assert event["delta_graph"]["updated_nodes"][0]["id"] == "E_ACQ_101"

    def test_push_auto_generates_iso_timestamp(self):
        eq = EventQueue()
        eq.push("act1", "N1", {"ripple_path": [], "insights": [], "delta_graph": {}})

        history = eq.get_history()
        ts = history[0]["timestamp"]
        # Should parse as a valid ISO datetime
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None

    def test_multiple_pushes_chronological_order(self):
        eq = EventQueue()
        eq.push("act1", "N1", {"ripple_path": ["N1"], "insights": [], "delta_graph": {}})
        eq.push("act2", "N2", {"ripple_path": ["N2", "N3"], "insights": [{"text": "x"}], "delta_graph": {}})

        history = eq.get_history()
        assert len(history) == 2
        assert history[0]["action_id"] == "act1"
        assert history[1]["action_id"] == "act2"
        # Chronological: first timestamp <= second timestamp
        assert history[0]["timestamp"] <= history[1]["timestamp"]

    def test_clear(self):
        eq = EventQueue()
        eq.push("act1", "N1", {"ripple_path": [], "insights": [], "delta_graph": {}})
        eq.push("act2", "N2", {"ripple_path": [], "insights": [], "delta_graph": {}})
        assert len(eq.get_history()) == 2

        eq.clear()
        assert eq.get_history() == []

    def test_push_with_missing_result_keys_uses_defaults(self):
        eq = EventQueue()
        eq.push("act1", "N1", {})

        history = eq.get_history()
        assert len(history) == 1
        assert history[0]["ripple_path"] == []
        assert history[0]["insights"] == []
        assert history[0]["delta_graph"] == {}

    def test_get_history_returns_dicts_not_dataclasses(self):
        eq = EventQueue()
        eq.push("act1", "N1", {"ripple_path": [], "insights": [], "delta_graph": {}})

        history = eq.get_history()
        assert isinstance(history[0], dict)
        expected_keys = {"timestamp", "action_id", "target_node_id", "ripple_path", "insights", "delta_graph"}
        assert set(history[0].keys()) == expected_keys


# ---------------------------------------------------------------------------
# Integration: EventQueue in OntologyEngine
# ---------------------------------------------------------------------------


class TestEventQueueInEngine:
    """Test that OntologyEngine records events via its event_queue."""

    @staticmethod
    def _build_simple_schema():
        return {
            "metadata": {"domain": "test", "version": "1.0", "description": "Test"},
            "ontology_def": {
                "node_types": {"Company": {"label": "公司", "color": "#4A90D9", "shape": "circle"}},
                "edge_types": {},
            },
            "graph_data": {
                "nodes": [
                    {"id": "C1", "type": "Company", "properties": {"name": "Alpha", "status": "ACTIVE"}},
                ],
                "edges": [],
            },
            "action_engine": {
                "actions": [
                    {
                        "action_id": "set_status",
                        "target_node_type": "Company",
                        "display_name": "Set Status",
                        "direct_effect": {"property_to_update": "status", "new_value": "INACTIVE"},
                        "ripple_rules": [],
                    }
                ]
            },
        }

    def test_execute_action_pushes_event(self):
        from app.engine.graph_engine import OntologyEngine

        engine = OntologyEngine()
        engine.load_workspace(self._build_simple_schema())

        assert engine.event_queue.get_history() == []

        engine.execute_action("set_status", "C1")

        history = engine.event_queue.get_history()
        assert len(history) == 1
        assert history[0]["action_id"] == "set_status"
        assert history[0]["target_node_id"] == "C1"
        assert history[0]["ripple_path"] == ["C1"]

    def test_two_executions_produce_two_events(self):
        from app.engine.graph_engine import OntologyEngine

        engine = OntologyEngine()
        schema = self._build_simple_schema()
        engine.load_workspace(schema)

        engine.execute_action("set_status", "C1")
        engine.execute_action("set_status", "C1")

        history = engine.event_queue.get_history()
        assert len(history) == 2
        assert all(e["action_id"] == "set_status" for e in history)
        # Each has complete ripple_path and insights
        for e in history:
            assert "ripple_path" in e
            assert "insights" in e

    def test_error_action_does_not_push_event(self):
        from app.engine.graph_engine import OntologyEngine

        engine = OntologyEngine()
        engine.load_workspace(self._build_simple_schema())

        result = engine.execute_action("nonexistent_action", "C1")
        assert result["status"] == "error"
        # No event recorded for failed actions
        assert engine.event_queue.get_history() == []

    def test_event_contains_insights_and_delta_graph(self):
        from app.engine.graph_engine import OntologyEngine
        from app.engine.action_registry import register_action, ActionContext, ActionResult
        import types

        @register_action
        def set_property(ctx: ActionContext) -> ActionResult:
            prop = ctx.params["property"]
            old = ctx.target_node.get(prop)
            return ActionResult(
                updated_properties={prop: ctx.params["value"]},
                old_values={prop: old} if old is not None else {},
            )

        action_module = types.ModuleType("test_actions")
        action_module.set_property = set_property

        schema = {
            "metadata": {"domain": "test", "version": "1.0", "description": "Test"},
            "ontology_def": {
                "node_types": {
                    "Event": {"label": "事件", "color": "#F00", "shape": "diamond"},
                    "Company": {"label": "公司", "color": "#00F", "shape": "circle"},
                },
                "edge_types": {
                    "TARGET_OF": {"label": "关联", "color": "#999", "style": "solid"},
                },
            },
            "graph_data": {
                "nodes": [
                    {"id": "E1", "type": "Event", "properties": {"status": "PENDING"}},
                    {"id": "C1", "type": "Company", "properties": {"name": "Alpha", "risk_status": "NORMAL"}},
                ],
                "edges": [
                    {"source": "C1", "target": "E1", "type": "TARGET_OF", "properties": {}},
                ],
            },
            "action_engine": {
                "actions": [
                    {
                        "action_id": "trigger_event",
                        "target_node_type": "Event",
                        "display_name": "Trigger",
                        "direct_effect": {"property_to_update": "status", "new_value": "FAILED"},
                        "ripple_rules": [
                            {
                                "rule_id": "R1",
                                "propagation_path": "<-[TARGET_OF]- Company",
                                "condition": None,
                                "effect_on_target": {
                                    "action_to_trigger": "set_property",
                                    "parameters": {"property": "risk_status", "value": "HIGH_RISK"},
                                },
                                "insight_template": "{target[name]} is now at risk",
                                "insight_type": "risk_propagation",
                                "insight_severity": "critical",
                            }
                        ],
                    }
                ]
            },
        }

        engine = OntologyEngine()
        engine.load_workspace(schema, action_module=action_module)
        engine.execute_action("trigger_event", "E1")

        history = engine.event_queue.get_history()
        assert len(history) == 1
        event = history[0]
        assert len(event["insights"]) >= 1
        assert event["insights"][0]["type"] == "risk_propagation"
        assert len(event["delta_graph"]["updated_nodes"]) >= 1
        assert "E1" in event["ripple_path"]
        assert "C1" in event["ripple_path"]
