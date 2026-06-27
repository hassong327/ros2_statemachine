from __future__ import annotations

import importlib
from typing import Any, Type


def import_message_class(type_name: str) -> Type[Any]:
    """Import a ROS 2 Python message class from a common type string."""

    normalized = type_name.strip()
    if "/msg/" in normalized:
        package, class_name = normalized.split("/msg/", maxsplit=1)
        module_name = f"{package}.msg"
    elif "/" in normalized:
        package, class_name = normalized.split("/", maxsplit=1)
        module_name = f"{package}.msg"
    elif ".msg." in normalized:
        module_name, class_name = normalized.rsplit(".", maxsplit=1)
    else:
        raise ValueError(
            f"Unsupported message type '{type_name}'. "
            "Use forms like 'std_msgs/msg/String'."
        )

    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def get_field(message: Any, field_path: str) -> Any:
    target = message
    for field in field_path.split("."):
        target = getattr(target, field)
    return target


def set_field(message: Any, field_path: str, value: Any) -> None:
    parts = field_path.split(".")
    target = message
    for field in parts[:-1]:
        target = getattr(target, field)

    leaf = parts[-1]
    current = getattr(target, leaf)
    setattr(target, leaf, coerce_like(current, value))


def coerce_like(current_value: Any, value: Any) -> Any:
    """Coerce YAML values into the type expected by simple ROS message fields."""

    if isinstance(current_value, bool):
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        return int(value)
    if isinstance(current_value, float):
        return float(value)
    if isinstance(current_value, str):
        return str(value)
    return value
