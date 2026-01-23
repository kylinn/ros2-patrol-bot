import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_navigation = get_package_share_directory('patrol_robot_navigation')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    slam_params_file = LaunchConfiguration('slam_params_file')

    default_slam_params = os.path.join(pkg_navigation, 'config', 'slam_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),

        DeclareLaunchArgument(
            'slam_params_file',
            default_value=default_slam_params,
            description='Full path to the SLAM parameters file'
        ),

        # SLAM Toolbox node
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[
                slam_params_file,
                {'use_sim_time': use_sim_time}
            ],
        ),
    ])
