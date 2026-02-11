"""Tests for ActionRegistry, ActionContext, ActionResult, and @register_action."""

import types

import networkx as nx

from app.engine.action_registry import (
    ActionContext,
    ActionRegistry,
    ActionResult,
    register_action,
)


# --- Helper: a test module with decorated functions ---

@register_action
def dummy_action(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        updated_properties={"status": "DONE"},
        old_values={"status": "PENDING"},
    )


@register_action
def another_action(ctx: ActionContext) -> ActionResult:
    return ActionResult()


def not_an_action(ctx: ActionContext) -> ActionResult:
    """This function is NOT decorated, so it should NOT be registered."""
    return ActionResult()


# --- Tests ---


class TestRegisterActionDecorator:
    def test_marks_is_action(self):
        assert getattr(dummy_action, "_is_action", False) is True

    def test_marks_action_name(self):
        assert getattr(dummy_action, "_action_name", None) == "dummy_action"

    def test_undecorated_has_no_marker(self):
        assert getattr(not_an_action, "_is_action", False) is False


class TestActionContext:
    def test_fields(self):
        g = nx.DiGraph()
        ctx = ActionContext(
            target_node={"id": "n1", "type": "Company"},
            source_node={"id": "n2", "type": "Event"},
            target_id="n1",
            source_id="n2",
            params={"factor": 0.7},
            graph=g,
        )
        assert ctx.target_id == "n1"
        assert ctx.source_id == "n2"
        assert ctx.params["factor"] == 0.7
        assert isinstance(ctx.graph, nx.DiGraph)


class TestActionResult:
    def test_defaults(self):
        r = ActionResult()
        assert r.updated_properties == {}
        assert r.old_values == {}

    def test_with_values(self):
        r = ActionResult(
            updated_properties={"val": 100},
            old_values={"val": 200},
        )
        assert r.updated_properties["val"] == 100
        assert r.old_values["val"] == 200


class TestActionRegistry:
    def test_register_and_get(self):
        registry = ActionRegistry()
        registry.register("my_func", dummy_action)
        assert registry.get("my_func") is dummy_action

    def test_get_unregistered_returns_none(self):
        registry = ActionRegistry()
        assert registry.get("nonexistent") is None

    def test_list_actions_empty(self):
        registry = ActionRegistry()
        assert registry.list_actions() == []

    def test_register_from_module(self):
        """Create a fake module with decorated functions, register, and verify."""
        mod = types.ModuleType("fake_module")
        mod.dummy_action = dummy_action
        mod.another_action = another_action
        mod.not_an_action = not_an_action

        registry = ActionRegistry()
        registry.register_from_module(mod)

        # Decorated functions should be registered
        assert registry.get("dummy_action") is dummy_action
        assert registry.get("another_action") is another_action

        # Undecorated function should NOT be registered
        assert registry.get("not_an_action") is None

    def test_list_actions_sorted(self):
        mod = types.ModuleType("fake_module")
        mod.dummy_action = dummy_action
        mod.another_action = another_action

        registry = ActionRegistry()
        registry.register_from_module(mod)

        names = registry.list_actions()
        assert names == ["another_action", "dummy_action"]

    def test_register_from_real_module_style(self):
        """Simulate importing a module object directly (like action_functions)."""
        # Build a module-like namespace
        import sys
        mod = types.ModuleType("test_actions")
        mod.dummy_action = dummy_action
        mod.another_action = another_action
        mod.not_an_action = not_an_action
        sys.modules["test_actions"] = mod

        registry = ActionRegistry()
        import test_actions
        registry.register_from_module(test_actions)

        assert set(registry.list_actions()) == {"dummy_action", "another_action"}
        assert registry.get("dummy_action")(None) == ActionResult(
            updated_properties={"status": "DONE"},
            old_values={"status": "PENDING"},
        )

        del sys.modules["test_actions"]
