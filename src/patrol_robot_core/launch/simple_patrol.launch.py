#!/usr/bin/env python3
"""
Launch file for simple patrol node (without Nav2)
Works directly with Gazebo Sim
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share = get_package_share_directory('patrol_robot_core')
    config_file = os.path.join(pkg_share, 'config', 'patrol_config.yaml')

    return LaunchDescription([
        # Declare arguments
        DeclareLaunchArgument(
            'output_dir',
            default_value='/tmp/patrol_images',
            description='Directory to save patrol images'
        ),

        # Simple patrol node
        Node(
            package='patrol_robot_core',
            executable='simple_patrol.py',
            name='simple_patrol_node',
            output='screen',
            parameters=[
                config_file,
                {'output_dir': LaunchConfiguration('output_dir')}
            ]
        ),

        # Audio player node (optional)
        Node(
            package='patrol_robot_core',
            executable='audio_player_node.py',
            name='audio_player_node',
            output='screen'
        ),
    ])
