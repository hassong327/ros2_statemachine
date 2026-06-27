from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rclpy.node import Node

from state_machine.message_utils import import_message_class, set_field


@dataclass(frozen=True)
class OutputSpec:
    name: str
    topic: str
    type_name: str
    field: str = "data"
    qos_depth: int = 10


class TopicOutput:
    """Publisher wrapper for one command output topic."""

    def __init__(self, node: Node, spec: OutputSpec) -> None:
        self.spec = spec
        self.msg_cls = import_message_class(spec.type_name)
        self.publisher = node.create_publisher(self.msg_cls, spec.topic, spec.qos_depth)

    def publish_value(self, value: Any) -> None:
        msg = self.msg_cls()
        set_field(msg, self.spec.field, value)
        self.publisher.publish(msg)


@dataclass(frozen=True)
class TopicAction:
    """Action that publishes a configured value to a configured output."""

    output_name: str
    value: Any

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopicAction":
        if "output" not in data:
            raise ValueError("action requires 'output'")
        if "value" not in data:
            raise ValueError("action requires 'value'")
        return cls(output_name=str(data["output"]), value=data["value"])

    def execute(self, outputs: dict[str, TopicOutput], node: Node) -> None:
        output = outputs.get(self.output_name)
        if output is None:
            node.get_logger().error(f"Unknown action output '{self.output_name}'")
            return
        output.publish_value(self.value)
        node.get_logger().info(
            f"Published action output={self.output_name} "
            f"topic={output.spec.topic} value={self.value}"
        )
