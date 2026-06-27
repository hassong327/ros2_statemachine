# state_machine

Configurable topic-driven ROS 2 state machine package.

The node reads a YAML file, subscribes to configured input topics, stores the
latest topic values in a context, evaluates state transition conditions, and
publishes command values to configured output topics.

## Run

```bash
ros2 launch state_machine state_machine.launch.py
```

Use a custom config:

```bash
ros2 launch state_machine state_machine.launch.py config_file:=/path/to/state_machine.yaml
```

## Example

The default config listens to:

- `/traffic_light` (`std_msgs/msg/String`)
- `/obstacle_detected` (`std_msgs/msg/Bool`)

It publishes:

- `/behavior_cmd` (`std_msgs/msg/String`)
- `/state_machine/current_state` (`std_msgs/msg/String`)

Example publishers:

```bash
ros2 topic pub /traffic_light std_msgs/msg/String "{data: GREEN}" --once
ros2 topic pub /obstacle_detected std_msgs/msg/Bool "{data: true}" --once
ros2 topic echo /behavior_cmd
ros2 topic echo /state_machine/current_state
```
