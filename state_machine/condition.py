from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from state_machine.context import StateContext


@dataclass(frozen=True)
class TopicCondition:
    """A branch condition evaluated against one stored input value."""

    input_name: str
    op: str
    expected: Any = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopicCondition":
        if "input" not in data:
            raise ValueError("condition requires 'input'")
        op = str(data.get("op", "=="))
        return cls(input_name=str(data["input"]), op=op, expected=data.get("value"))

    def evaluate(self, context: StateContext) -> bool:
        if self.op == "exists":
            return context.has_input(self.input_name)
        if self.op == "not_exists":
            return not context.has_input(self.input_name)
        if not context.has_input(self.input_name):
            return False

        actual = context.get_input(self.input_name)
        expected = _coerce_for_compare(actual, self.expected)

        if self.op == "==":
            return actual == expected
        if self.op == "!=":
            return actual != expected
        if self.op == ">":
            return actual > expected
        if self.op == ">=":
            return actual >= expected
        if self.op == "<":
            return actual < expected
        if self.op == "<=":
            return actual <= expected
        raise ValueError(f"Unsupported condition op '{self.op}'")


@dataclass(frozen=True)
class ConditionGroup:
    """Supports single, all, or any condition forms from YAML."""

    mode: str
    conditions: tuple[TopicCondition, ...]

    @classmethod
    def from_yaml(cls, data: Any) -> "ConditionGroup":
        if isinstance(data, dict) and "all" in data:
            return cls("all", tuple(TopicCondition.from_dict(item) for item in data["all"]))
        if isinstance(data, dict) and "any" in data:
            return cls("any", tuple(TopicCondition.from_dict(item) for item in data["any"]))
        if isinstance(data, dict):
            return cls("all", (TopicCondition.from_dict(data),))
        raise ValueError("transition 'when' must be a condition dictionary")

    def evaluate(self, context: StateContext) -> bool:
        if self.mode == "any":
            return any(condition.evaluate(context) for condition in self.conditions)
        return all(condition.evaluate(context) for condition in self.conditions)


def _coerce_for_compare(actual: Any, expected: Any) -> Any:
    if expected is None:
        return None
    if isinstance(actual, bool):
        if isinstance(expected, str):
            return expected.lower() in ("true", "1", "yes", "on")
        return bool(expected)
    if isinstance(actual, int) and not isinstance(actual, bool):
        return int(expected)
    if isinstance(actual, float):
        return float(expected)
    if isinstance(actual, str):
        return str(expected)
    return expected
