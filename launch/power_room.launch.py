#!/usr/bin/env python3
"""
Launch file for TurtleBot3 in Power Distribution Room
25m x 20m room with 40 high-voltage cabinets
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # Get package directories
    turtlebot3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    gazebo_ros_dir = get_package_share_directory('gazebo_ros')

    # World file path - use absolute path for Windows/WSL compatibility
    world_file = '/mnt/d/TbbRobot/worlds/power_room.world'

    # Robot initial position (center of the room, near control desk)
    x_pose = LaunchConfiguration('x_pose', default='-8.0')
    y_pose = LaunchConfiguration('y_pose', default='0.0')

    # Set Gazebo model path to include our custom models
    gazebo_model_path = SetEnvironmentVariable(
        'GAZEBO_MODEL_PATH',
        os.path.join('/mnt/d/TbbRobot/models') + ':' +
        os.environ.get('GAZEBO_MODEL_PATH', '')
    )

    # Launch Gazebo server
    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_dir, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={'world': world_file}.items()
    )

    # Launch Gazebo client
    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_dir, 'launch', 'gzclient.launch.py')
        )
    )

    # Spawn TurtleBot3
    spawn_turtlebot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_gazebo_dir, 'launch', 'spawn_turtlebot3.launch.py')
        ),
        launch_arguments={
            'x_pose': x_pose,
            'y_pose': y_pose
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument('x_pose', default_value='-8.0'),
        DeclareLaunchArgument('y_pose', default_value='0.0'),
        gazebo_model_path,
        gzserver,
        gzclient,
        spawn_turtlebot,
    ])
