#!/usr/bin/env python3
"""
升降杆 ros2_control 客户端
使用 JointTrajectoryController Action 接口控制升降杆
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Duration
import sys


class LiftControlClient(Node):
    def __init__(self):
        super().__init__('lift_control_client')

        # Action 客户端
        self._action_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/lift_controller/follow_joint_trajectory'
        )

        # 当前关节位置
        self.current_lift = 0.0
        self.current_tilt = 0.0

        # 订阅关节状态
        self.joint_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_callback,
            10
        )

        self.get_logger().info('升降杆 ros2_control 客户端已启动')
        self.get_logger().info('等待 Action 服务器...')
        self._action_client.wait_for_server()
        self.get_logger().info('Action 服务器已连接')

    def joint_callback(self, msg: JointState):
        """更新当前关节位置"""
        for i, name in enumerate(msg.name):
            if name == 'lift_joint':
                self.current_lift = msg.position[i]
            elif name == 'tilt_joint':
                self.current_tilt = msg.position[i]

    def send_goal(self, lift_pos: float, tilt_pos: float, duration: float = 3.0):
        """发送目标位置"""
        # 限制范围
        lift_pos = max(0.0, min(2.0, lift_pos))
        tilt_pos = max(-1.57, min(0.5, tilt_pos))

        # 创建轨迹
        trajectory = JointTrajectory()
        trajectory.joint_names = ['lift_joint', 'tilt_joint']

        point = JointTrajectoryPoint()
        point.positions = [lift_pos, tilt_pos]
        point.velocities = [0.0, 0.0]
        point.time_from_start = Duration(
            sec=int(duration),
            nanosec=int((duration % 1) * 1e9)
        )
        trajectory.points = [point]

        # 创建 Goal
        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory = trajectory

        self.get_logger().info(
            f'发送目标: lift={lift_pos:.2f}m, tilt={tilt_pos:.2f}rad, 时间={duration:.1f}s'
        )

        # 发送 Goal
        send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('目标被拒绝')
            return

        self.get_logger().info('目标已接受')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info(f'运动完成, 错误码: {result.error_code}')
        self.get_logger().info(
            f'当前位置: lift={self.current_lift:.3f}m, tilt={self.current_tilt:.3f}rad'
        )

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        if feedback.actual.positions:
            self.get_logger().debug(
                f'进度: lift={feedback.actual.positions[0]:.3f}m'
            )


def main(args=None):
    rclpy.init(args=args)
    client = LiftControlClient()

    # 解析命令行参数
    if len(sys.argv) >= 3:
        lift_pos = float(sys.argv[1])
        tilt_pos = float(sys.argv[2])
        duration = float(sys.argv[3]) if len(sys.argv) >= 4 else 3.0
        client.send_goal(lift_pos, tilt_pos, duration)
    else:
        print('用法: python3 lift_ros2_control_client.py <lift_height> <tilt_angle> [duration]')
        print('示例:')
        print('  升起: python3 lift_ros2_control_client.py 1.8 -0.2 3.0')
        print('  收回: python3 lift_ros2_control_client.py 0.0 0.0 3.0')
        # 默认演示：升起
        client.send_goal(1.8, -0.2, 3.0)

    try:
        rclpy.spin(client)
    except KeyboardInterrupt:
        pass
    finally:
        client.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
