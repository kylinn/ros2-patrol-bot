#!/usr/bin/env python3
"""
简单建图节点 - 沿走廊安全建图
避开设备密集区，只在走廊中移动
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
import subprocess
import os
import math


class SimpleMapping(Node):
    def __init__(self):
        super().__init__('simple_mapping')

        self.declare_parameter('map_save_path', '/mnt/d/TbbRobot/maps/power_room')
        self.map_save_path = self.get_parameter('map_save_path').value

        # State
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.min_front_dist = float('inf')

        # 纯墙边建图路径 - 只沿着四面墙移动
        # 配电室约 20m x 10m，原点在中心
        # 设备在中间，必须完全避开
        self.commands = [
            # === 1. 起点扫描 (原点附近) ===
            ('spin', 360),

            # === 2. 先到南墙 (y=-4.5) ===
            ('spin', 180),          # 转向南 (负Y方向)
            ('forward', 4.0),       # 走到南墙附近
            ('spin', 360),          # 扫描

            # === 3. 沿南墙向西走到西南角 ===
            ('spin', 90),           # 转向西 (负X方向)
            ('forward', 8.0),       # 走到西墙
            ('spin', 360),          # 扫描西南角

            # === 4. 沿西墙向北走 ===
            ('spin', -90),          # 转向北 (正Y方向)
            ('forward', 3.0),       # 走一段
            ('spin', 360),          # 扫描
            ('forward', 3.0),       # 继续向北
            ('spin', 360),          # 扫描
            ('forward', 3.0),       # 到西北角
            ('spin', 360),          # 扫描西北角

            # === 5. 沿北墙向东走 ===
            ('spin', -90),          # 转向东 (正X方向)
            ('forward', 4.0),       # 走一段
            ('spin', 360),          # 扫描
            ('forward', 4.0),       # 继续
            ('spin', 360),          # 扫描
            ('forward', 4.0),       # 继续
            ('spin', 360),          # 扫描
            ('forward', 4.0),       # 到东北角
            ('spin', 360),          # 扫描东北角

            # === 6. 沿东墙向南走 ===
            ('spin', 90),           # 转向南 (负Y方向)
            ('forward', 3.0),       # 走一段
            ('spin', 360),          # 扫描
            ('forward', 3.0),       # 继续
            ('spin', 360),          # 扫描
            ('forward', 3.0),       # 到东南角
            ('spin', 360),          # 扫描东南角

            # === 7. 沿南墙返回原点方向 ===
            ('spin', 90),           # 转向西
            ('forward', 4.0),       # 走一段
            ('spin', 360),          # 扫描
            ('forward', 4.0),       # 回到原点下方
            ('spin', 360),          # 最终扫描
        ]

        self.cmd_idx = 0
        self.cmd_start_time = None
        self.cmd_start_yaw = None
        self.cmd_start_x = None
        self.cmd_start_y = None
        self.obstacle_count = 0

        # Publishers/Subscribers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)

        self.get_logger().info('=== 简单建图节点 (走廊版) ===')
        self.get_logger().info(f'地图保存路径: {self.map_save_path}')
        self.get_logger().info(f'共 {len(self.commands)} 个动作')

        self.get_logger().info('等待传感器数据...')
        self.startup_timer = self.create_timer(1.0, self.check_ready)

    def check_ready(self):
        if hasattr(self, '_wait_count'):
            self._wait_count += 1
            if self._wait_count > 3:
                self.startup_timer.cancel()
                self.get_logger().info('传感器就绪，开始建图!')
                self.control_timer = self.create_timer(0.1, self.control_loop)
        else:
            self._wait_count = 1

    def odom_cb(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        self.yaw = math.atan2(siny_cosp, cosy_cosp)

    def scan_cb(self, msg):
        ranges = msg.ranges
        n = len(ranges)
        # 前方 ±30度
        front_indices = list(range(0, n // 12)) + list(range(11 * n // 12, n))
        front_ranges = [ranges[i] for i in front_indices
                       if not math.isnan(ranges[i]) and ranges[i] > 0.1]
        self.min_front_dist = min(front_ranges) if front_ranges else float('inf')

    def control_loop(self):
        if self.cmd_idx >= len(self.commands):
            self.finish_mapping()
            return

        cmd_type, cmd_value = self.commands[self.cmd_idx]
        twist = Twist()

        if self.cmd_start_time is None:
            self.cmd_start_time = self.get_clock().now()
            self.cmd_start_yaw = self.yaw
            self.cmd_start_x = self.x
            self.cmd_start_y = self.y
            self.accumulated_rotation = 0.0
            self.last_yaw = self.yaw
            self.obstacle_count = 0
            self.get_logger().info(
                f'[{self.cmd_idx + 1}/{len(self.commands)}] {cmd_type} {cmd_value} '
                f'(当前位置: {self.x:.1f}, {self.y:.1f})')

        if cmd_type == 'spin':
            delta = self.normalize_angle(self.yaw - self.last_yaw)
            self.accumulated_rotation += abs(delta)
            self.last_yaw = self.yaw

            target_angle = math.radians(abs(cmd_value))
            if self.accumulated_rotation >= target_angle * 0.95:
                self.next_command()
                return
            twist.angular.z = 0.4 if cmd_value > 0 else -0.4

        elif cmd_type == 'forward':
            dx = self.x - self.cmd_start_x
            dy = self.y - self.cmd_start_y
            traveled = math.sqrt(dx * dx + dy * dy)

            # 检测障碍物
            if self.min_front_dist < 0.4:
                self.obstacle_count += 1
                if self.obstacle_count > 30:  # 3秒无法通过
                    self.get_logger().warn(
                        f'前方障碍物 ({self.min_front_dist:.2f}m)，已走 {traveled:.2f}m，跳过')
                    self.next_command()
                    return
                # 减速
                twist.linear.x = 0.05
            else:
                self.obstacle_count = 0
                if traveled >= cmd_value * 0.95:
                    self.next_command()
                    return
                twist.linear.x = 0.2

        self.cmd_vel_pub.publish(twist)

    def normalize_angle(self, angle):
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle

    def next_command(self):
        self.cmd_vel_pub.publish(Twist())
        self.cmd_idx += 1
        self.cmd_start_time = None

    def finish_mapping(self):
        if hasattr(self, 'control_timer'):
            self.control_timer.cancel()
        self.cmd_vel_pub.publish(Twist())
        self.get_logger().info('=== 建图完成! ===')
        self.get_logger().info(f'最终位置: ({self.x:.2f}, {self.y:.2f})')
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
    node = SimpleMapping()
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
