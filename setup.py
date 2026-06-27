from glob import glob
from setuptools import setup

package_name = "state_machine"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/launch", glob("launch/*.py")),
    ],
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    maintainer="songha",
    maintainer_email="songha@example.com",
    description="Configurable topic-driven ROS 2 state machine.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "state_machine_node = state_machine.node:main",
        ],
    },
)
