from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from state_machine.action import OutputSpec, TopicAction
from state_machine.condition import ConditionGroup


@dataclass(frozen=True)
class InputSpec:
    name: str
    topic: str
    type_name: str
    field: str = "data"
    qos_depth: int = 10


@dataclass(frozen=True)
class TransitionSpec:
    condition: ConditionGroup
    target_state: str
    actions: tuple[TopicAction, ...] = ()


@dataclass(frozen=True)
class StateSpec:
    name: str
    on_enter: tuple[TopicAction, ...] = ()
    transitions: tuple[TransitionSpec, ...] = ()


@dataclass(frozen=True)
class StateMachineConfig:
    initial_state: str
    update_rate_hz: float
    status_topic: str
    inputs: dict[str, InputSpec] = field(default_factory=dict)
    outputs: dict[str, OutputSpec] = field(default_factory=dict)
    states: dict[str, StateSpec] = field(default_factory=dict)


def load_config(path: str | Path) -> StateMachineConfig:
    config_path = Path(path).expanduser()
    with config_path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream) or {}

    root = _extract_root(raw)
    initial_state = str(root.get("initial_state", "IDLE"))
    update_rate_hz = float(root.get("update_rate_hz", 10.0))
    status_topic = str(root.get("status_topic", "~/current_state"))

    inputs = {
        name: _parse_input(name, data)
        for name, data in (root.get("inputs") or {}).items()
    }
    outputs = {
        name: _parse_output(name, data)
        for name, data in (root.get("outputs") or {}).items()
    }
    states = {
        name: _parse_state(name, data)
        for name, data in (root.get("states") or {}).items()
    }

    config = StateMachineConfig(
        initial_state=initial_state,
        update_rate_hz=update_rate_hz,
        status_topic=status_topic,
        inputs=inputs,
        outputs=outputs,
        states=states,
    )
    _validate_config(config)
    return config


def _extract_root(raw: dict[str, Any]) -> dict[str, Any]:
    if "state_machine" not in raw:
        return raw

    root = raw["state_machine"] or {}
    if "ros__parameters" in root:
        params = root["ros__parameters"] or {}
        if "state_machine" in params:
            return params["state_machine"] or {}
        return params
    return root


def _parse_input(name: str, data: dict[str, Any]) -> InputSpec:
    return InputSpec(
        name=str(name),
        topic=str(_required(data, "topic", f"input '{name}'")),
        type_name=str(_required(data, "type", f"input '{name}'")),
        field=str(data.get("field", "data")),
        qos_depth=int(data.get("qos_depth", 10)),
    )


def _parse_output(name: str, data: dict[str, Any]) -> OutputSpec:
    return OutputSpec(
        name=str(name),
        topic=str(_required(data, "topic", f"output '{name}'")),
        type_name=str(_required(data, "type", f"output '{name}'")),
        field=str(data.get("field", "data")),
        qos_depth=int(data.get("qos_depth", 10)),
    )


def _parse_state(name: str, data: dict[str, Any] | None) -> StateSpec:
    data = data or {}
    on_enter = tuple(TopicAction.from_dict(item) for item in data.get("on_enter", []))
    transitions = tuple(_parse_transition(item) for item in data.get("transitions", []))
    return StateSpec(name=str(name), on_enter=on_enter, transitions=transitions)


def _parse_transition(data: dict[str, Any]) -> TransitionSpec:
    if "to" not in data:
        raise ValueError("transition requires 'to'")
    if "when" not in data:
        raise ValueError("transition requires 'when'")
    actions = tuple(TopicAction.from_dict(item) for item in data.get("actions", []))
    return TransitionSpec(
        condition=ConditionGroup.from_yaml(data["when"]),
        target_state=str(data["to"]),
        actions=actions,
    )


def _validate_config(config: StateMachineConfig) -> None:
    if config.update_rate_hz <= 0.0:
        raise ValueError("update_rate_hz must be greater than zero")
    if config.initial_state not in config.states:
        raise ValueError(f"initial_state '{config.initial_state}' is not defined in states")

    output_names = set(config.outputs)
    input_names = set(config.inputs)
    state_names = set(config.states)

    for state in config.states.values():
        _validate_actions(state.on_enter, output_names, f"state '{state.name}' on_enter")
        for transition in state.transitions:
            if transition.target_state not in state_names:
                raise ValueError(
                    f"state '{state.name}' transition target "
                    f"'{transition.target_state}' is not defined"
                )
            _validate_condition_inputs(transition.condition, input_names, state.name)
            _validate_actions(
                transition.actions,
                output_names,
                f"state '{state.name}' transition to '{transition.target_state}'",
            )


def _validate_condition_inputs(
    condition: ConditionGroup, input_names: set[str], state_name: str
) -> None:
    for item in condition.conditions:
        if item.input_name not in input_names:
            raise ValueError(
                f"state '{state_name}' references unknown input '{item.input_name}'"
            )


def _validate_actions(
    actions: tuple[TopicAction, ...], output_names: set[str], location: str
) -> None:
    for action in actions:
        if action.output_name not in output_names:
            raise ValueError(f"{location} references unknown output '{action.output_name}'")


def _required(data: dict[str, Any], key: str, owner: str) -> Any:
    if key not in data:
        raise ValueError(f"{owner} requires '{key}'")
    return data[key]
