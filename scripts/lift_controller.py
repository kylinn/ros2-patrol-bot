#!/usr/bin/env python3
"""
升降杆控制器 - 提供升降杆和云台的控制服务
用于商业化巡检流程：到点停车 -> 升杆 -> 调整俯仰 -> 拍照 -> 收杆 -> 移动
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState, Image
from std_srvs.srv import Trigger
from builtin_interfaces.msg import Duration
import json
import threading
import time


class LiftController(Node):
    def __init__(self):
        super().__init__('lift_controller')

        self.callback_group = ReentrantCallbackGroup()

        # 当前关节状态
        self.current_lift_pos = 0.0
        self.current_tilt_pos = 0.0
        self.target_lift_pos = 0.0
        self.target_tilt_pos = 0.0

        # 运动状态
        self.is_moving = False
        self.move_complete = threading.Event()

        # 订阅关节状态
        self.joint_state_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10,
            callback_group=self.callback_group
        )

        # 发布升降杆轨迹命令
        self.lift_pub = self.create_publisher(
            JointTrajectory,
            '/lift_controller/command',
            10
        )

        # 保存最新图像
        self.latest_image = None
        self.image_sub = self.create_subscription(
            Image,
            '/inspection_camera/image_raw',
            self.image_callback,
            10,
            callback_group=self.callback_group
        )

        # 创建服务
        self.raise_srv = self.create_service(
            Trigger,
            '/lift/raise',
            self.raise_callback,
            callback_group=self.callback_group
        )

        self.lower_srv = self.create_service(
            Trigger,
            '/lift/lower',
            self.lower_callback,
            callback_group=self.callback_group
        )

        self.capture_srv = self.create_service(
            Trigger,
            '/lift/capture',
            self.capture_callback,
            callback_group=self.callback_group
        )

        # 定时器检查运动完成
        self.check_timer = self.create_timer(
            0.1,
            self.check_motion_complete,
            callback_group=self.callback_group
        )

        # 默认参数
        self.default_lift_height = 1.8  # 默认升起高度 1.8m
        self.default_tilt_angle = -0.3  # 默认俯仰角 -17度（略微向下看）
        self.position_tolerance = 0.05  # 位置容差

        self.get_logger().info('升降杆控制器已启动')
        self.get_logger().info(f'  默认升起高度: {self.default_lift_height}m')
        self.get_logger().info(f'  默认俯仰角度: {self.default_tilt_angle}rad')

    def joint_state_callback(self, msg: JointState):
        """更新当前关节状态"""
        for i, name in enumerate(msg.name):
            if name == 'lift_joint':
                self.current_lift_pos = msg.position[i]
            elif name == 'tilt_joint':
                self.current_tilt_pos = msg.position[i]

    def image_callback(self, msg: Image):
        """保存最新图像"""
        self.latest_image = msg

    def check_motion_complete(self):
        """检查运动是否完成"""
        if self.is_moving:
            lift_error = abs(self.current_lift_pos - self.target_lift_pos)
            tilt_error = abs(self.current_tilt_pos - self.target_tilt_pos)

            if lift_error < self.position_tolerance and tilt_error < self.position_tolerance:
                self.is_moving = False
                self.move_complete.set()
                self.get_logger().info(
                    f'运动完成: lift={self.current_lift_pos:.3f}m, tilt={self.current_tilt_pos:.3f}rad'
                )

    def send_trajectory(self, lift_pos: float, tilt_pos: float, duration_sec: float = 3.0):
        """发送关节轨迹命令"""
        # 限制范围
        lift_pos = max(0.0, min(2.0, lift_pos))
        tilt_pos = max(-1.57, min(0.5, tilt_pos))

        self.target_lift_pos = lift_pos
        self.target_tilt_pos = tilt_pos
        self.is_moving = True
        self.move_complete.clear()

        # 创建轨迹消息
        traj = JointTrajectory()
        traj.joint_names = ['lift_joint', 'tilt_joint']

        point = JointTrajectoryPoint()
        point.positions = [lift_pos, tilt_pos]
        point.velocities = [0.0, 0.0]
        point.time_from_start = Duration(sec=int(duration_sec), nanosec=int((duration_sec % 1) * 1e9))

        traj.points = [point]

        self.lift_pub.publish(traj)
        self.get_logger().info(
            f'发送轨迹命令: lift={lift_pos:.2f}m, tilt={tilt_pos:.2f}rad, duration={duration_sec:.1f}s'
        )

    def raise_callback(self, request, response):
        """升起升降杆服务"""
        self.get_logger().info('收到升杆请求')

        # 发送升起命令
        self.send_trajectory(self.default_lift_height, self.default_tilt_angle, 3.0)

        # 等待完成（最多等待10秒）
        success = self.move_complete.wait(timeout=10.0)

        if success:
            response.success = True
            response.message = f'升降杆已升起至 {self.current_lift_pos:.2f}m'
        else:
            response.success = False
            response.message = f'升杆超时，当前位置: {self.current_lift_pos:.2f}m'

        return response

    def lower_callback(self, request, response):
        """收回升降杆服务"""
        self.get_logger().info('收到收杆请求')

        # 发送收回命令（先复位俯仰角，再收杆）
        self.send_trajectory(0.0, 0.0, 3.0)

        # 等待完成
        success = self.move_complete.wait(timeout=10.0)

        if success:
            response.success = True
            response.message = '升降杆已收回'
        else:
            response.success = False
            response.message = f'收杆超时，当前位置: {self.current_lift_pos:.2f}m'

        return response

    def capture_callback(self, request, response):
        """拍照服务"""
        self.get_logger().info('收到拍照请求')

        if self.latest_image is not None:
            # 实际应用中这里会保存图像或发送到分析服务
            response.success = True
            response.message = f'已捕获图像 {self.latest_image.width}x{self.latest_image.height}'
            self.get_logger().info(f'图像已捕获: {self.latest_image.width}x{self.latest_image.height}')
        else:
            response.success = False
            response.message = '未收到相机图像'

        return response


def main(args=None):
    rclpy.init(args=args)
    node = LiftController()

    # 使用多线程执行器以支持并发服务调用
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
