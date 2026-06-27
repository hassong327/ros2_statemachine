from __future__ import annotations

from pathlib import Path
from typing import Any

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from state_machine.action import TopicOutput
from state_machine.config_loader import InputSpec, StateMachineConfig, load_config
from state_machine.context import StateContext
from state_machine.message_utils import get_field, import_message_class


class GenericStateMachineNode(Node):
    """Configurable topic-driven state machine node."""

    def __init__(self) -> None:
        super().__init__("state_machine")
        self.declare_parameter("config_file", "")

        config_file = self.get_parameter("config_file").get_parameter_value().string_value
        if not config_file:
            config_file = str(
                Path(get_package_share_directory("state_machine"))
                / "config"
                / "state_machine.yaml"
            )

        self.config = load_config(config_file)
        self.context = StateContext(self.config.initial_state)

        self.outputs = {
            name: TopicOutput(self, spec)
            for name, spec in self.config.outputs.items()
        }
        self.subscriptions_by_input = {}

        state_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self.state_pub = self.create_publisher(String, self.config.status_topic, state_qos)

        for spec in self.config.inputs.values():
            self._create_input_subscription(spec)

        self._last_transition_time = self.get_clock().now()
        self._publish_current_state()
        self._execute_actions(
            self.config.states[self.config.initial_state].on_enter,
            "initial on_enter",
        )

        period = 1.0 / self.config.update_rate_hz
        self.timer = self.create_timer(period, self._on_timer)

        self.get_logger().info(
            "state_machine started config=%s initial_state=%s update_rate_hz=%.3f",
            config_file,
            self.config.initial_state,
            self.config.update_rate_hz,
        )

    def _create_input_subscription(self, spec: InputSpec) -> None:
        msg_cls = import_message_class(spec.type_name)

        def callback(msg: Any, input_spec: InputSpec = spec) -> None:
            try:
                value = get_field(msg, input_spec.field)
            except AttributeError as exc:
                self.get_logger().error(
                    f"Failed to read field '{input_spec.field}' "
                    f"from input '{input_spec.name}': {exc}"
                )
                return

            self.context.set_input(input_spec.name, value)
            self.get_logger().debug(f"input {input_spec.name}={value}")

        self.subscriptions_by_input[spec.name] = self.create_subscription(
            msg_cls,
            spec.topic,
            callback,
            spec.qos_depth,
        )
        self.get_logger().info(
            f"Subscribed input={spec.name} topic={spec.topic} "
            f"type={spec.type_name} field={spec.field}"
        )

    def _on_timer(self) -> None:
        try:
            self._evaluate_transitions()
        except Exception as exc:  # noqa: BLE001 - keep node alive on config/runtime errors.
            self.get_logger().error(f"state machine evaluation error: {exc}")

    def _evaluate_transitions(self) -> None:
        current_state = self.context.get_state()
        state = self.config.states.get(current_state)
        if state is None:
            self.get_logger().error(f"Current state '{current_state}' is not configured")
            return

        for transition in state.transitions:
            if not transition.condition.evaluate(self.context):
                continue

            previous_state = current_state
            target_state = transition.target_state
            self.context.set_state(target_state)
            self._last_transition_time = self.get_clock().now()
            self._publish_current_state()

            self.get_logger().info(
                f"transition from={previous_state} to={target_state} "
                f"inputs={self.context.snapshot()['inputs']}"
            )

            self._execute_actions(
                transition.actions,
                f"transition {previous_state}->{target_state}",
            )

            if target_state != previous_state:
                self._execute_actions(
                    self.config.states[target_state].on_enter,
                    f"on_enter {target_state}",
                )
            return

    def _execute_actions(self, actions: tuple[Any, ...], reason: str) -> None:
        for action in actions:
            self.get_logger().debug(f"execute action reason={reason} action={action}")
            action.execute(self.outputs, self)

    def _publish_current_state(self) -> None:
        msg = String()
        msg.data = self.context.get_state()
        self.state_pub.publish(msg)

    def get_state_age(self) -> Duration:
        return self.get_clock().now() - self._last_transition_time


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = GenericStateMachineNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
