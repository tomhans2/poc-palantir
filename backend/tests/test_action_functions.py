"""Tests for action_functions.py — L1/L2/L3 action functions."""

import pytest
import networkx as nx

from app.engine.action_registry import ActionContext, ActionResult, ActionRegistry, register_action
from app.actions import action_functions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(target_node: dict, params: dict, graph: nx.DiGraph | None = None,
              source_node: dict | None = None, target_id: str = "T1",
              source_id: str = "S1") -> ActionContext:
    return ActionContext(
        target_node=target_node,
        source_node=source_node or {},
        target_id=target_id,
        source_id=source_id,
        params=params,
        graph=graph or nx.DiGraph(),
    )


# ---------------------------------------------------------------------------
# L1: set_property
# ---------------------------------------------------------------------------

class TestSetProperty:
    def test_basic(self):
        ctx = _make_ctx(
            target_node={"status": "ACTIVE"},
            params={"property": "status", "value": "FAILED"},
        )
        result = action_functions.set_property(ctx)
        assert isinstance(result, ActionResult)
        assert result.updated_properties == {"status": "FAILED"}
        assert result.old_values == {"status": "ACTIVE"}

    def test_missing_property_returns_none_old_value(self):
        ctx = _make_ctx(
            target_node={},
            params={"property": "status", "value": "FAILED"},
        )
        result = action_functions.set_property(ctx)
        assert result.updated_properties == {"status": "FAILED"}
        assert result.old_values == {"status": None}


# ---------------------------------------------------------------------------
# L1: adjust_numeric
# ---------------------------------------------------------------------------

class TestAdjustNumeric:
    def test_basic(self):
        ctx = _make_ctx(
            target_node={"valuation": 10_000_000},
            params={"property": "valuation", "factor": 0.7},
        )
        result = action_functions.adjust_numeric(ctx)
        assert result.updated_properties["valuation"] == 7_000_000
        assert result.old_values["valuation"] == 10_000_000

    def test_factor_greater_than_one(self):
        ctx = _make_ctx(
            target_node={"valuation": 100},
            params={"property": "valuation", "factor": 1.5},
        )
        result = action_functions.adjust_numeric(ctx)
        assert result.updated_properties["valuation"] == 150

    def test_missing_property_defaults_to_zero(self):
        ctx = _make_ctx(
            target_node={},
            params={"property": "valuation", "factor": 0.7},
        )
        result = action_functions.adjust_numeric(ctx)
        assert result.updated_properties["valuation"] == 0
        assert result.old_values["valuation"] == 0


# ---------------------------------------------------------------------------
# L1: update_risk_status
# ---------------------------------------------------------------------------

class TestUpdateRiskStatus:
    def test_basic(self):
        ctx = _make_ctx(
            target_node={"risk_status": "LOW_RISK"},
            params={"status": "HIGH_RISK"},
        )
        result = action_functions.update_risk_status(ctx)
        assert result.updated_properties == {"risk_status": "HIGH_RISK"}
        assert result.old_values == {"risk_status": "LOW_RISK"}

    def test_default_status(self):
        ctx = _make_ctx(
            target_node={"risk_status": "NORMAL"},
            params={},
        )
        result = action_functions.update_risk_status(ctx)
        assert result.updated_properties["risk_status"] == "HIGH_RISK"


# ---------------------------------------------------------------------------
# L2: recalculate_valuation
# ---------------------------------------------------------------------------

class TestRecalculateValuation:
    def test_negative_shock(self):
        ctx = _make_ctx(
            target_node={"valuation": 1_000_000},
            params={"shock_factor": -0.3},
        )
        result = action_functions.recalculate_valuation(ctx)
        assert result.updated_properties["valuation"] == 700_000
        assert result.old_values["valuation"] == 1_000_000

    def test_positive_shock(self):
        ctx = _make_ctx(
            target_node={"valuation": 1_000_000},
            params={"shock_factor": 0.2},
        )
        result = action_functions.recalculate_valuation(ctx)
        assert result.updated_properties["valuation"] == 1_200_000

    def test_zero_shock(self):
        ctx = _make_ctx(
            target_node={"valuation": 500},
            params={"shock_factor": 0},
        )
        result = action_functions.recalculate_valuation(ctx)
        assert result.updated_properties["valuation"] == 500


# ---------------------------------------------------------------------------
# L2: compute_margin_gap
# ---------------------------------------------------------------------------

class TestComputeMarginGap:
    def test_basic(self):
        ctx = _make_ctx(
            target_node={"loan_amount": 1_000_000, "collateral_ratio": 1.5},
            params={"stock_change": -0.4},
        )
        result = action_functions.compute_margin_gap(ctx)
        # margin_gap = 1_000_000 * (1 - 1.5 * (1 + (-0.4)))
        #            = 1_000_000 * (1 - 1.5 * 0.6)
        #            = 1_000_000 * (1 - 0.9)
        #            = 1_000_000 * 0.1 = 100_000
        assert result.updated_properties["margin_gap"] == pytest.approx(100_000)
        assert result.old_values["loan_amount"] == 1_000_000
        assert result.old_values["collateral_ratio"] == 1.5

    def test_no_gap_when_stock_rises(self):
        ctx = _make_ctx(
            target_node={"loan_amount": 1_000_000, "collateral_ratio": 1.5},
            params={"stock_change": 0.5},
        )
        result = action_functions.compute_margin_gap(ctx)
        # margin_gap = 1_000_000 * (1 - 1.5 * 1.5) = 1_000_000 * (1 - 2.25) = -1_250_000
        assert result.updated_properties["margin_gap"] == -1_250_000


# ---------------------------------------------------------------------------
# L3: graph_weighted_exposure
# ---------------------------------------------------------------------------

class TestGraphWeightedExposure:
    def _build_test_graph(self) -> nx.DiGraph:
        """Build a graph with 3 nodes: T1 -> N1 (weight=0.5), T1 -> N2 (weight=0.3)."""
        g = nx.DiGraph()
        g.add_node("T1", type="Company", valuation=1000, exposure=0)
        g.add_node("N1", type="Company", valuation=500)
        g.add_node("N2", type="Company", valuation=200)
        g.add_edge("T1", "N1", type="SUPPLIES_TO", weight=0.5)
        g.add_edge("T1", "N2", type="SUPPLIES_TO", weight=0.3)
        return g

    def test_sum_aggregation(self):
        g = self._build_test_graph()
        ctx = _make_ctx(
            target_node=dict(g.nodes["T1"]),
            params={
                "direction": "out",
                "edge_type": "SUPPLIES_TO",
                "value_property": "valuation",
                "weight_property": "weight",
                "aggregation": "sum",
            },
            graph=g,
            target_id="T1",
        )
        result = action_functions.graph_weighted_exposure(ctx)
        # 500*0.5 + 200*0.3 = 250 + 60 = 310
        assert result.updated_properties["exposure"] == 310.0

    def test_max_aggregation(self):
        g = self._build_test_graph()
        ctx = _make_ctx(
            target_node=dict(g.nodes["T1"]),
            params={
                "direction": "out",
                "edge_type": "SUPPLIES_TO",
                "aggregation": "max",
            },
            graph=g,
            target_id="T1",
        )
        result = action_functions.graph_weighted_exposure(ctx)
        # max(500*0.5, 200*0.3) = max(250, 60) = 250
        assert result.updated_properties["exposure"] == 250.0

    def test_count_aggregation(self):
        g = self._build_test_graph()
        ctx = _make_ctx(
            target_node=dict(g.nodes["T1"]),
            params={
                "direction": "out",
                "edge_type": "SUPPLIES_TO",
                "aggregation": "count",
            },
            graph=g,
            target_id="T1",
        )
        result = action_functions.graph_weighted_exposure(ctx)
        assert result.updated_properties["exposure"] == 2

    def test_incoming_direction(self):
        g = nx.DiGraph()
        g.add_node("T1", type="Company", valuation=0, exposure=0)
        g.add_node("N1", type="Company", valuation=800)
        g.add_edge("N1", "T1", type="SUPPLIES_TO", weight=0.4)
        ctx = _make_ctx(
            target_node=dict(g.nodes["T1"]),
            params={"direction": "in", "edge_type": "SUPPLIES_TO"},
            graph=g,
            target_id="T1",
        )
        result = action_functions.graph_weighted_exposure(ctx)
        # 800 * 0.4 = 320
        assert result.updated_properties["exposure"] == 320.0

    def test_edge_type_filter(self):
        """Only edges matching edge_type should be considered."""
        g = self._build_test_graph()
        g.add_edge("T1", "N1", type="OWNS", weight=1.0)
        ctx = _make_ctx(
            target_node=dict(g.nodes["T1"]),
            params={"direction": "out", "edge_type": "OWNS", "aggregation": "sum"},
            graph=g,
            target_id="T1",
        )
        result = action_functions.graph_weighted_exposure(ctx)
        # Only the OWNS edge: 500 * 1.0 = 500
        assert result.updated_properties["exposure"] == 500.0

    def test_no_matching_edges(self):
        g = self._build_test_graph()
        ctx = _make_ctx(
            target_node=dict(g.nodes["T1"]),
            params={"direction": "out", "edge_type": "NONEXISTENT"},
            graph=g,
            target_id="T1",
        )
        result = action_functions.graph_weighted_exposure(ctx)
        assert result.updated_properties["exposure"] == 0.0


# ---------------------------------------------------------------------------
# Registration: all functions discoverable via @register_action
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_all_functions_registered(self):
        registry = ActionRegistry()
        registry.register_from_module(action_functions)
        names = registry.list_actions()
        expected = sorted([
            "set_property",
            "adjust_numeric",
            "update_risk_status",
            "recalculate_valuation",
            "compute_margin_gap",
            "graph_weighted_exposure",
        ])
        assert names == expected

    def test_get_returns_callable(self):
        registry = ActionRegistry()
        registry.register_from_module(action_functions)
        for name in ["set_property", "adjust_numeric", "recalculate_valuation",
                      "compute_margin_gap", "graph_weighted_exposure", "update_risk_status"]:
            func = registry.get(name)
            assert callable(func), f"{name} should be callable"
