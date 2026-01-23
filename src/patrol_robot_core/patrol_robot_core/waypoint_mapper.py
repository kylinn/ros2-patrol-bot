#!/usr/bin/env python3
"""
Waypoint-based 建图节点
简单可靠：按预定义路径遍历房间，让 SLAM Toolbox 建图
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import Twist
import subprocess
import os


class WaypointMapper(Node):
    def __init__(self):
        super().__init__('waypoint_mapper')

        # Parameters
        self.declare_parameter('map_save_path', '/mnt/d/TbbRobot/maps/indoor_office')
        self.map_save_path = self.get_parameter('map_save_path').value

        # 10x10m 房间 waypoints（房间范围 -5 到 +5）
        # 使用更保守的路点，避开墙壁
        self.waypoints = [
            # 中心区域
            (0.0, 0.0),
            (1.5, 0.0),
            (1.5, 1.5),
            (0.0, 1.5),
            (-1.5, 1.5),
            (-1.5, 0.0),
            (-1.5, -1.5),
            (0.0, -1.5),
            (1.5, -1.5),
            # 扩展探索
            (2.5, 0.0),
            (2.5, 2.5),
            (0.0, 2.5),
            (-2.5, 2.5),
            (-2.5, 0.0),
            (-2.5, -2.5),
            (0.0, -2.5),
            (2.5, -2.5),
            # 回到原点
            (0.0, 0.0),
        ]
        self.current_wp = 0
        self.navigating = False
        self.goal_handle = None
        self.timeout_timer = None
        self.scan_timer = None
        self.finished = False

        # Nav2 action client
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Cmd vel for spinning
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.get_logger().info('=== Waypoint 建图节点 ===')
        self.get_logger().info(f'地图保存路径: {self.map_save_path}')
        self.get_logger().info(f'共 {len(self.waypoints)} 个路点')

        # Wait for Nav2
        self.get_logger().info('等待 Nav2...')
        self.startup_timer = self.create_timer(2.0, self.try_start)

    def try_start(self):
        if self.nav_client.server_is_ready():
            self.startup_timer.cancel()
            self.get_logger().info('Nav2 就绪，开始建图!')
            self.initial_spin()
        else:
            self.get_logger().info('等待 Nav2...')

    def initial_spin(self):
        """初始旋转扫描"""
        self.get_logger().info('原地旋转扫描...')
        twist = Twist()
        twist.angular.z = 0.5
        self.cmd_vel_pub.publish(twist)
        self.spin_timer = self.create_timer(10.0, self.after_initial_spin)

    def after_initial_spin(self):
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None
        self.cmd_vel_pub.publish(Twist())
        self.get_logger().info('初始扫描完成')
        self.navigate_to_next()

    def navigate_to_next(self):
        """导航到下一个 waypoint"""
        if self.finished:
            return

        if self.current_wp >= len(self.waypoints):
            self.finish_mapping()
            return

        x, y = self.waypoints[self.current_wp]
        self.get_logger().info(
            f'[{self.current_wp + 1}/{len(self.waypoints)}] 导航到 ({x:.1f}, {y:.1f})')

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.orientation.w = 1.0

        self.navigating = True
        future = self.nav_client.send_goal_async(goal)
        future.add_done_callback(self.goal_response_callback)

        # Timeout 45s
        if self.timeout_timer:
            self.timeout_timer.cancel()
        self.timeout_timer = self.create_timer(45.0, self.nav_timeout)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('目标被拒绝，跳过')
            self.cancel_timeout()
            self.next_waypoint()
            return
        self.goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.goal_result_callback)

    def goal_result_callback(self, future):
        if self.finished or not self.navigating:
            return

        self.cancel_timeout()
        self.navigating = False

        result = future.result()
        status = result.status

        x, y = self.waypoints[self.current_wp]

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'成功到达 ({x:.1f}, {y:.1f})，扫描中...')
            self.do_scan_then_next()
        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().warn(f'无法到达 ({x:.1f}, {y:.1f})，跳过')
            self.next_waypoint()
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info(f'导航取消: ({x:.1f}, {y:.1f})')
            self.next_waypoint()
        else:
            self.get_logger().warn(f'导航状态: {status}，跳过')
            self.next_waypoint()

    def do_scan_then_next(self):
        """到达后扫描然后下一个点"""
        twist = Twist()
        twist.angular.z = 0.5
        self.cmd_vel_pub.publish(twist)
        if self.scan_timer:
            self.scan_timer.cancel()
        self.scan_timer = self.create_timer(5.0, self.after_scan)

    def after_scan(self):
        if self.scan_timer:
            self.scan_timer.cancel()
            self.scan_timer = None
        self.cmd_vel_pub.publish(Twist())
        self.next_waypoint()

    def cancel_timeout(self):
        if self.timeout_timer:
            self.timeout_timer.cancel()
            self.timeout_timer = None

    def nav_timeout(self):
        if self.finished or not self.navigating:
            return
        self.get_logger().warn('导航超时，跳过当前点')
        self.cancel_timeout()
        if self.goal_handle:
            self.goal_handle.cancel_goal_async()
        self.navigating = False
        self.next_waypoint()

    def next_waypoint(self):
        if self.finished:
            return
        self.current_wp += 1
        self.navigate_to_next()

    def finish_mapping(self):
        if self.finished:
            return
        self.finished = True
        self.get_logger().info('=== 建图完成! ===')
        self.cmd_vel_pub.publish(Twist())
        self.save_map()

    def save_map(self):
        map_dir = os.path.dirname(self.map_save_path)
        os.makedirs(map_dir, exist_ok=True)
        self.get_logger().info('保存地图...')

        try:
            cmd = [
                'ros2', 'run', 'nav2_map_server', 'map_saver_cli',
                '-f', self.map_save_path,
                '--ros-args', '-p', 'use_sim_time:=true'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.get_logger().info(f'地图保存成功: {self.map_save_path}')
            else:
                self.get_logger().error(f'保存失败: {result.stderr}')
        except Exception as e:
            self.get_logger().error(f'错误: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = WaypointMapper()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('中断，保存地图...')
        node.save_map()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
