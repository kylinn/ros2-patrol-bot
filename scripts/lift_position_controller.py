#!/usr/bin/env python3
"""
升降杆位置控制器 - 使用 PID 控制实现位置控制
通过 /apply_joint_effort 服务控制关节位置
"""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from gazebo_msgs.srv import ApplyJointEffort, JointRequest
from builtin_interfaces.msg import Duration, Time
import threading
import time


class LiftPositionController(Node):
    def __init__(self):
        super().__init__('lift_position_controller')

        self.callback_group = ReentrantCallbackGroup()

        # 目标位置
        self.target_lift = 0.0
        self.target_tilt = 0.0

        # 当前位置
        self.current_lift = 0.0
        self.current_tilt = 0.0

        # PID 参数
        self.lift_kp = 50.0   # 升降杆 P 增益
        self.lift_kd = 30.0   # 升降杆 D 增益
        self.lift_gravity_comp = 13.0  # 重力补偿 (~1.3kg * 9.8)
        self.tilt_kp = 10.0   # 俯仰 P 增益
        self.tilt_kd = 3.0    # 俯仰 D 增益

        # 上次误差 (用于 D 控制)
        self.last_lift_error = 0.0
        self.last_tilt_error = 0.0

        # 订阅关节状态
        self.joint_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_callback,
            10,
            callback_group=self.callback_group
        )

        # 订阅轨迹命令 (与 Web 界面兼容)
        self.traj_sub = self.create_subscription(
            JointTrajectory,
            '/lift_controller/command',
            self.trajectory_callback,
            10,
            callback_group=self.callback_group
        )

        # 创建服务客户端
        self.effort_client = self.create_client(
            ApplyJointEffort,
            '/apply_joint_effort',
            callback_group=self.callback_group
        )

        self.clear_client = self.create_client(
            JointRequest,
            '/clear_joint_efforts',
            callback_group=self.callback_group
        )

        # 等待服务可用
        while not self.effort_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('等待 /apply_joint_effort 服务...')

        # 控制定时器 (50Hz)
        self.control_timer = self.create_timer(
            0.02,
            self.control_loop,
            callback_group=self.callback_group
        )

        self.get_logger().info('升降杆位置控制器已启动')
        self.get_logger().info(f'  Lift PID: Kp={self.lift_kp}, Kd={self.lift_kd}')
        self.get_logger().info(f'  Tilt PID: Kp={self.tilt_kp}, Kd={self.tilt_kd}')

    def joint_callback(self, msg: JointState):
        """更新当前关节位置"""
        for i, name in enumerate(msg.name):
            if name == 'lift_joint':
                self.current_lift = msg.position[i]
            elif name == 'tilt_joint':
                self.current_tilt = msg.position[i]

    def trajectory_callback(self, msg: JointTrajectory):
        """处理轨迹命令"""
        if len(msg.points) == 0:
            return

        point = msg.points[0]
        for i, name in enumerate(msg.joint_names):
            if i >= len(point.positions):
                continue
            if name == 'lift_joint':
                self.target_lift = max(0.0, min(2.0, point.positions[i]))
                self.get_logger().info(f'设置升降杆目标: {self.target_lift:.2f}m')
            elif name == 'tilt_joint':
                self.target_tilt = max(-1.57, min(0.5, point.positions[i]))
                self.get_logger().info(f'设置俯仰角目标: {self.target_tilt:.2f}rad')

    def control_loop(self):
        """PID 控制循环"""
        # 升降杆控制 (带重力补偿)
        lift_error = self.target_lift - self.current_lift
        lift_deriv = lift_error - self.last_lift_error
        lift_effort = self.lift_kp * lift_error + self.lift_kd * lift_deriv + self.lift_gravity_comp
        lift_effort = max(-50.0, min(100.0, lift_effort))
        self.last_lift_error = lift_error

        # 俯仰控制
        tilt_error = self.target_tilt - self.current_tilt
        tilt_deriv = tilt_error - self.last_tilt_error
        tilt_effort = self.tilt_kp * tilt_error + self.tilt_kd * tilt_deriv
        tilt_effort = max(-10.0, min(10.0, tilt_effort))
        self.last_tilt_error = tilt_error

        # 应用力矩
        self.apply_effort('lift_joint', lift_effort)
        self.apply_effort('tilt_joint', tilt_effort)

    def apply_effort(self, joint_name: str, effort: float):
        """应用关节力矩"""
        request = ApplyJointEffort.Request()
        # 使用完整的模型名::关节名格式
        request.joint_name = f'turtlebot3_custom::{joint_name}'
        request.effort = effort
        request.start_time = Time(sec=0, nanosec=0)
        request.duration = Duration(sec=0, nanosec=50000000)  # 50ms

        # 异步调用
        self.effort_client.call_async(request)


def main(args=None):
    rclpy.init(args=args)
    node = LiftPositionController()

    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
