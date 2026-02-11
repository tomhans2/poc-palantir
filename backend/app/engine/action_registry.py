from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import inspect

import networkx as nx


@dataclass
class ActionContext:
    """Context passed to each action function during execution."""
    target_node: dict
    source_node: dict
    target_id: str
    source_id: str
    params: dict[str, Any]
    graph: nx.DiGraph


@dataclass
class ActionResult:
    """Result returned by an action function."""
    updated_properties: dict[str, Any] = field(default_factory=dict)
    old_values: dict[str, Any] = field(default_factory=dict)


def register_action(func: Callable) -> Callable:
    """Decorator that marks a function as a registrable action."""
    func._is_action = True
    func._action_name = func.__name__
    return func


class ActionRegistry:
    """Registry for action functions that can be looked up by name."""

    def __init__(self) -> None:
        self._actions: dict[str, Callable] = {}
        self._sources: dict[str, str] = {}

    def register(self, name: str, func: Callable, source: str = "builtin") -> None:
        """Register a callable under the given name with a source label."""
        self._actions[name] = func
        self._sources[name] = source

    def register_from_module(self, module: object, source: str = "builtin") -> None:
        """Scan a module for callables marked with @register_action and register them."""
        for _name, obj in inspect.getmembers(module, callable):
            if getattr(obj, "_is_action", False):
                action_name = getattr(obj, "_action_name", obj.__name__)
                self.register(action_name, obj, source=source)

    def get(self, name: str) -> Optional[Callable]:
        """Return the action function registered under name, or None."""
        return self._actions.get(name)

    def list_actions(self) -> list[str]:
        """Return a sorted list of all registered action names."""
        return sorted(self._actions.keys())

    def list_actions_with_source(self) -> list[dict[str, str]]:
        """Return a sorted list of registered actions with their source labels."""
        return sorted(
            [{"name": name, "source": self._sources.get(name, "builtin")} for name in self._actions],
            key=lambda x: x["name"],
        )
