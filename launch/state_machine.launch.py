from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    config_file = LaunchConfiguration("config_file")

    default_config = PathJoinSubstitution(
        [FindPackageShare("state_machine"), "config", "state_machine.yaml"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "config_file",
                default_value=default_config,
                description="Path to the state machine YAML config file.",
            ),
            Node(
                package="state_machine",
                executable="state_machine_node",
                name="state_machine",
                output="screen",
                parameters=[{"config_file": config_file}],
            ),
        ]
    )
