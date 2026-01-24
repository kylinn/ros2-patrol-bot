#!/usr/bin/env python3
"""
升降杆控制器启动文件
使用 ros2_control + joint_trajectory_controller
"""

from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessStart
from launch_ros.actions import Node


def generate_launch_description():
    # 启动 controller_manager 的控制器
    # 注意：controller_manager 由 gazebo_ros2_control 插件自动启动

    # 加载并启动 joint_state_broadcaster
    load_joint_state_broadcaster = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'joint_state_broadcaster'],
        output='screen'
    )

    # 加载并启动 lift_controller (JointTrajectoryController)
    load_lift_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'lift_controller'],
        output='screen'
    )

    # 延迟启动控制器，等待 controller_manager 就绪
    delayed_joint_state = TimerAction(
        period=3.0,
        actions=[load_joint_state_broadcaster]
    )

    delayed_lift_controller = TimerAction(
        period=5.0,
        actions=[load_lift_controller]
    )

    return LaunchDescription([
        delayed_joint_state,
        delayed_lift_controller,
    ])
