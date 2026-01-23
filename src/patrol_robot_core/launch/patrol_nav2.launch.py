import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('patrol_robot_gazebo')
    pkg_core = get_package_share_directory('patrol_robot_core')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Config files
    nav2_params_file = os.path.join(pkg_gazebo, 'config', 'nav2_params.yaml')
    patrol_config_file = os.path.join(pkg_core, 'config', 'patrol_config.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use simulation time'),

        # 1. Launch Gazebo with robot
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo, 'launch', 'gazebo.launch.py')
            ),
        ),

        # 2. Launch Nav2 + SLAM (delayed to wait for Gazebo)
        TimerAction(
            period=10.0,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(pkg_gazebo, 'launch', 'nav2_slam.launch.py')
                    ),
                    launch_arguments={
                        'use_sim_time': 'true',
                    }.items()
                ),
            ]
        ),

        # 3. Launch patrol node (delayed further to wait for Nav2)
        TimerAction(
            period=30.0,
            actions=[
                Node(
                    package='patrol_robot_core',
                    executable='patrol_node',
                    name='patrol_node',
                    output='screen',
                    parameters=[patrol_config_file, {'use_sim_time': use_sim_time}],
                ),
            ]
        ),
    ])
