import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_bringup = get_package_share_directory('patrol_robot_bringup')
    pkg_gazebo = get_package_share_directory('patrol_robot_gazebo')
    pkg_navigation = get_package_share_directory('patrol_robot_navigation')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    map_file = LaunchConfiguration('map')

    # RViz config
    rviz_config = os.path.join(pkg_bringup, 'rviz', 'navigation.rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),

        DeclareLaunchArgument(
            'map',
            default_value='',
            description='Full path to map yaml file'
        ),

        # Launch Gazebo simulation
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'use_sim_time': use_sim_time}.items()
        ),

        # Launch Nav2 navigation
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_navigation, 'launch', 'navigation.launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'map': map_file,
            }.items()
        ),

        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'
        ),
    ])
