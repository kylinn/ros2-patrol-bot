import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_navigation = get_package_share_directory('patrol_robot_navigation')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    slam = LaunchConfiguration('slam')
    map_file = LaunchConfiguration('map')
    nav2_params_file = LaunchConfiguration('params_file')

    default_nav2_params = os.path.join(pkg_navigation, 'config', 'nav2_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),

        DeclareLaunchArgument(
            'slam',
            default_value='False',
            description='Whether to run SLAM (True) or localization (False)'
        ),

        DeclareLaunchArgument(
            'map',
            default_value='',
            description='Full path to map yaml file'
        ),

        DeclareLaunchArgument(
            'params_file',
            default_value=default_nav2_params,
            description='Full path to the Nav2 parameters file'
        ),

        # Nav2 bringup
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_nav2_bringup, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'slam': slam,
                'map': map_file,
                'params_file': nav2_params_file,
            }.items()
        ),
    ])
