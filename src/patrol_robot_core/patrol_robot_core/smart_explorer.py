#!/usr/bin/env python3
"""
智能自动探索建图节点
使用 Nav2 导航到预设的探索点位
类似扫地机器人的覆盖式探索
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
import math
import subprocess
import os


class SmartExplorer(Node):
    def __init__(self):
        super().__init__('smart_explorer')

        self.declare_parameter('map_save_path', '/mnt/d/TbbRobot/maps/power_room')
        self.map_save_path = self.get_parameter('map_save_path').value

        # Nav2 action client
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Map subscriber to monitor progress
        self.map_sub = self.create_subscription(
            OccupancyGrid, '/map', self.map_callback, 10)
        self.map_info = None

        # 200 sqm room (20m x 10m) exploration waypoints
        # Room: X from -10 to +10, Y from -5 to +5
        # Create a grid of exploration points
        self.waypoints = self.generate_exploration_waypoints()
        self.current_wp_idx = 0
        self.failed_waypoints = set()
        self.completed_waypoints = set()

        self.get_logger().info('=== 智能自动探索节点 ===')
        self.get_logger().info(f'共 {len(self.waypoints)} 个探索点')
        self.get_logger().info(f'地图保存路径: {self.map_save_path}')

        # Wait for Nav2
        self.get_logger().info('等待 Nav2 导航服务...')
        if self.nav_client.wait_for_server(timeout_sec=30.0):
            self.get_logger().info('Nav2 已就绪，开始探索!')
            self.explore_next()
        else:
            self.get_logger().error('无法连接到 Nav2 导航服务')

    def generate_exploration_waypoints(self):
        """Generate grid of exploration waypoints for the power room"""
        waypoints = []

        # Start with initial scan at origin
        waypoints.append((0.0, 0.0, 0.0))

        # Grid exploration - cover the room in a snake pattern
        # Y ranges: -4 to 4 (avoiding walls at -5 and 5)
        # X ranges: -9 to 9 (avoiding walls at -10 and 10)

        y_values = [-3.5, -1.5, 1.5, 3.5]
        x_values_forward = [-7.0, -4.0, -1.0, 2.0, 5.0, 8.0]
        x_values_backward = list(reversed(x_values_forward))

        forward = True
        for y in y_values:
            x_list = x_values_forward if forward else x_values_backward
            for x in x_list:
                # Calculate yaw to face the direction of travel
                yaw = 0.0 if forward else math.pi
                waypoints.append((x, y, yaw))
            forward = not forward

        # Add corner exploration points
        corners = [
            (-8.0, 3.5, math.pi/2),    # Northwest - facing north
            (8.0, 3.5, math.pi/2),     # Northeast
            (-8.0, -3.5, -math.pi/2),  # Southwest
            (8.0, -3.5, -math.pi/2),   # Southeast
        ]
        waypoints.extend(corners)

        # Return to origin
        waypoints.append((0.0, 0.0, 0.0))

        return waypoints

    def map_callback(self, msg):
        """Track map updates"""
        self.map_info = msg.info

    def explore_next(self):
        """Send robot to next exploration point"""
        # Skip failed and completed waypoints
        while self.current_wp_idx < len(self.waypoints):
            if self.current_wp_idx not in self.failed_waypoints:
                break
            self.current_wp_idx += 1

        if self.current_wp_idx >= len(self.waypoints):
            self.get_logger().info('=== 探索完成! ===')
            self.save_map()
            return

        x, y, yaw = self.waypoints[self.current_wp_idx]

        self.get_logger().info(
            f'[{self.current_wp_idx + 1}/{len(self.waypoints)}] '
            f'前往探索点 ({x:.1f}, {y:.1f})')

        # Create goal pose
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0

        # Convert yaw to quaternion
        goal_msg.pose.pose.orientation.x = 0.0
        goal_msg.pose.pose.orientation.y = 0.0
        goal_msg.pose.pose.orientation.z = math.sin(yaw / 2)
        goal_msg.pose.pose.orientation.w = math.cos(yaw / 2)

        # Send goal
        send_goal_future = self.nav_client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """Handle goal acceptance/rejection"""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn(f'目标被拒绝，跳过该点')
            self.failed_waypoints.add(self.current_wp_idx)
            self.current_wp_idx += 1
            self.explore_next()
            return

        self.get_logger().info('目标已接受，导航中...')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        """Handle navigation feedback"""
        pass  # Could add progress logging here

    def get_result_callback(self, future):
        """Handle navigation result"""
        result = future.result().result
        status = future.result().status

        if status == 4:  # SUCCEEDED
            self.get_logger().info('到达目标点!')
            self.completed_waypoints.add(self.current_wp_idx)
        else:
            self.get_logger().warn(f'导航失败 (状态: {status})，跳过该点')
            self.failed_waypoints.add(self.current_wp_idx)

        self.current_wp_idx += 1
        self.explore_next()

    def save_map(self):
        """Save the final map"""
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
            self.get_logger().error(f'保存错误: {e}')

        # Report statistics
        self.get_logger().info(f'统计: 完成 {len(self.completed_waypoints)} 个点, '
                              f'失败 {len(self.failed_waypoints)} 个点')


def main(args=None):
    rclpy.init(args=args)
    node = SmartExplorer()
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
