import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('patrol_robot_gazebo')
    pkg_description = get_package_share_directory('patrol_robot_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world = LaunchConfiguration('world')

    # Default world file - 200 sqm power distribution room
    default_world = os.path.join(pkg_gazebo, 'worlds', 'power_distribution_room.sdf')

    # URDF file
    xacro_file = os.path.join(pkg_description, 'urdf', 'patrol_robot.urdf.xacro')
    robot_description = Command(['xacro ', xacro_file])

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),

        DeclareLaunchArgument(
            'world',
            default_value=default_world,
            description='World file to load'
        ),

        # Launch Gazebo Sim
        # Note: --headless-rendering enables camera/depth sensors without GUI
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={
                'gz_args': ['-r --headless-rendering ', world],
                'on_exit_shutdown': 'true'
            }.items()
        ),

        # Robot State Publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'robot_description': robot_description
            }]
        ),

        # Spawn robot in Gazebo
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', 'patrol_robot',
                '-topic', 'robot_description',
                '-x', '0',
                '-y', '0',
                '-z', '0.1'
            ],
            output='screen'
        ),

        # Bridge for ROS-Gazebo communication
        # Direction: @ = bidirectional, [ = GZ->ROS, ] = ROS->GZ
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
                '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
                '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
                '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
                '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
                '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
                '/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
                '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            ],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'
        ),

        # Static TF to link Gazebo sensor frame to robot frame
        # Gazebo Sim uses patrol_robot/base_footprint/lidar but our URDF has lidar_link
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='lidar_frame_publisher',
            arguments=['0', '0', '0', '0', '0', '0', 'lidar_link', 'patrol_robot/base_footprint/lidar'],
            parameters=[{'use_sim_time': use_sim_time}],
        ),

        # Static TF for camera frame
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='camera_frame_publisher',
            arguments=['0', '0', '0', '0', '0', '0', 'camera_link', 'patrol_robot/base_footprint/camera_link/camera_sensor'],
            parameters=[{'use_sim_time': use_sim_time}],
        ),
    ])
