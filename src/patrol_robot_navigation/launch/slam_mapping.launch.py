import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_navigation = get_package_share_directory('patrol_robot_navigation')
    pkg_gazebo = get_package_share_directory('patrol_robot_gazebo')

    # RViz 配置文件路径
    rviz_config = os.path.join(pkg_navigation, 'config', 'slam_view.rviz')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    headless = LaunchConfiguration('headless', default='false')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('headless', default_value='false'),

        # 1. 启动 Gazebo 仿真
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'headless': headless}.items()
        ),

        # 2. 延迟启动 Nav2 (等待 Gazebo 就绪)
        TimerAction(
            period=10.0,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(pkg_navigation, 'launch', 'navigation.launch.py')
                    ),
                    launch_arguments={
                        'use_sim_time': use_sim_time,
                        'slam': 'True',
                    }.items()
                ),
            ]
        ),

        # 3. 启动 RViz2 实时可视化
        TimerAction(
            period=15.0,
            actions=[
                Node(
                    package='rviz2',
                    executable='rviz2',
                    name='rviz2',
                    arguments=['-d', rviz_config],
                    parameters=[{'use_sim_time': use_sim_time}],
                    output='screen'
                ),
            ]
        ),
    ])
