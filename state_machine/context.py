from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any


@dataclass
class StateContext:
    """Thread-safe storage for the current state and latest input values."""

    initial_state: str
    _current_state: str = field(init=False)
    _inputs: dict[str, Any] = field(default_factory=dict, init=False)
    _lock: RLock = field(default_factory=RLock, init=False)

    def __post_init__(self) -> None:
        self._current_state = self.initial_state

    def set_state(self, state: str) -> None:
        with self._lock:
            self._current_state = state

    def get_state(self) -> str:
        with self._lock:
            return self._current_state

    def set_input(self, name: str, value: Any) -> None:
        with self._lock:
            self._inputs[name] = value

    def get_input(self, name: str) -> Any:
        with self._lock:
            return self._inputs.get(name)

    def has_input(self, name: str) -> bool:
        with self._lock:
            return name in self._inputs

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "current_state": self._current_state,
                "inputs": dict(self._inputs),
            }
