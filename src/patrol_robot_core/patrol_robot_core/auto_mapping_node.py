#!/usr/bin/env python3
"""
自动建图节点 - 基于 Frontier Exploration（前沿探索）算法
原理：检测地图中已知区域和未知区域的边界（frontier），
     选择最近/最大的frontier作为目标，驱动机器人自动探索。
     定期回到起点帮助 SLAM 闭环，减少地图漂移。

这是 m-explore / explore_lite 等开源包的核心算法的简化实现。
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped, Twist, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid, Odometry
import numpy as np
import subprocess
import math
import time
import os
from collections import deque


class AutoMappingNode(Node):
    def __init__(self):
        super().__init__('auto_mapping_node')

        # Parameters
        self.declare_parameter('map_save_path', '/mnt/d/TbbRobot/maps/indoor_office')
        self.declare_parameter('exploration_time', 300.0)
        self.declare_parameter('min_frontier_size', 5)  # 最小frontier大小（格子数）
        self.declare_parameter('robot_radius', 0.2)
        self.declare_parameter('nav_timeout', 40.0)  # 导航超时时间
        self.declare_parameter('loop_closure_interval', 4)  # 每N次导航回一次起点

        self.map_save_path = self.get_parameter('map_save_path').value
        self.exploration_time = self.get_parameter('exploration_time').value
        self.min_frontier_size = self.get_parameter('min_frontier_size').value
        self.nav_timeout = self.get_parameter('nav_timeout').value
        self.loop_closure_interval = self.get_parameter('loop_closure_interval').value

        # State
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        self.map_data = None
        self.map_info = None
        self.exploring = False
        self.navigating = False
        self.start_time = None
        self.nav_goal_handle = None
        self.failed_goals = []  # 导航失败的目标
        self.no_frontier_count = 0
        self.nav_count = 0  # 导航计数，用于回环
        self.origin_x = 0.0  # 起点坐标
        self.origin_y = 0.0
        self.last_target = None  # 上次导航目标
        self.repeat_count = 0  # 连续重复目标次数
        self.spin_timer = None  # 旋转定时器引用

        # Nav2 action client
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Subscribers
        self.map_sub = self.create_subscription(
            OccupancyGrid, '/map', self.map_callback, 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)

        self.get_logger().info('=== 自动建图节点 (Frontier Exploration) ===')
        self.get_logger().info(f'地图保存路径: {self.map_save_path}')
        self.get_logger().info(f'最大探索时间: {self.exploration_time} 秒')
        self.get_logger().info(f'导航超时: {self.nav_timeout} 秒')
        self.get_logger().info(f'回环间隔: 每{self.loop_closure_interval}次导航回起点')

        # 等待 Nav2 就绪后开始
        self.get_logger().info('等待 Nav2 就绪...')
        self.startup_timer = self.create_timer(2.0, self.try_start)

    def try_start(self):
        """尝试启动探索"""
        if self.nav_client.server_is_ready():
            self.startup_timer.cancel()
            self.get_logger().info('Nav2 已就绪!')
            self.start_exploration()
        else:
            self.get_logger().info('等待 Nav2...')

    def odom_callback(self, msg):
        """里程计回调 - 获取机器人位置"""
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y
        # 提取yaw角
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.robot_yaw = math.atan2(siny_cosp, cosy_cosp)

    def map_callback(self, msg):
        """地图回调"""
        self.map_data = np.array(msg.data, dtype=np.int8).reshape(
            (msg.info.height, msg.info.width))
        self.map_info = msg.info

    def start_exploration(self):
        """开始自动探索"""
        self.get_logger().info('=== 开始 Frontier Exploration 自动建图 ===')
        self.exploring = True
        self.start_time = time.time()

        # 记录起点位置（用于回环）
        self.origin_x = self.robot_x
        self.origin_y = self.robot_y
        self.get_logger().info(f'起点记录: ({self.origin_x:.2f}, {self.origin_y:.2f})')

        # 先旋转一圈，获取初始地图
        self.get_logger().info('原地旋转获取初始激光扫描...')
        self.initial_spin()

    def initial_spin(self):
        """原地旋转360度获取初始激光数据"""
        spin_duration = 8.0  # 旋转时间
        spin_speed = 0.8  # 旋转速度 rad/s

        twist = Twist()
        twist.angular.z = spin_speed
        self.cmd_vel_pub.publish(twist)

        # 旋转完成后开始前沿探索（一次性定时器）
        self.spin_timer = self.create_timer(spin_duration, self.after_spin)

    def after_spin(self):
        """旋转完成后停止并开始探索"""
        # 取消定时器防止重复触发
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None

        # 停止旋转
        self.cmd_vel_pub.publish(Twist())
        self.get_logger().info('初始扫描完成，开始前沿探索...')

        # 启动探索循环（避免重复创建）
        if not hasattr(self, 'exploration_timer') or self.exploration_timer is None:
            self.exploration_timer = self.create_timer(3.0, self.exploration_step)

    def exploration_step(self):
        """探索步骤 - 寻找frontier并导航"""
        if not self.exploring:
            return

        # 检查时间
        elapsed = time.time() - self.start_time
        if elapsed >= self.exploration_time:
            self.get_logger().info(f'探索时间到 ({self.exploration_time:.0f}秒)')
            self.finish_exploration()
            return

        # 如果正在导航中，不重复发送目标
        if self.navigating:
            return

        # 检查是否有地图数据
        if self.map_data is None:
            self.get_logger().info('等待地图数据...')
            return

        # 回环策略：每N次导航回一次起点
        if (self.nav_count > 0 and
                self.nav_count % self.loop_closure_interval == 0 and
                self.distance_to(self.origin_x, self.origin_y) > 1.0):
            self.get_logger().info(
                f'=== 回环闭合: 返回起点 ({self.origin_x:.2f}, {self.origin_y:.2f}) ===')
            self.navigate_to_frontier(self.origin_x, self.origin_y)
            self.nav_count += 1  # 防止再次触发
            return

        # 寻找 frontiers
        frontiers = self.find_frontiers()

        if not frontiers:
            self.no_frontier_count += 1
            remaining = self.exploration_time - elapsed
            self.get_logger().info(
                f'未发现新的frontier (第{self.no_frontier_count}次) | '
                f'剩余时间: {remaining:.0f}秒')

            if self.no_frontier_count >= 8:
                self.get_logger().info('连续8次未发现frontier，探索完成!')
                self.finish_exploration()
            return

        self.no_frontier_count = 0

        # 选择最佳 frontier
        target = self.select_best_frontier(frontiers)

        if target:
            # 检查是否重复目标（距离上次目标<1m认为是同一个）
            if self.last_target:
                dist_to_last = math.sqrt(
                    (target[0] - self.last_target[0])**2 +
                    (target[1] - self.last_target[1])**2)
                if dist_to_last < 1.0:
                    self.repeat_count += 1
                    if self.repeat_count >= 3:
                        self.get_logger().warn(
                            f'目标 ({target[0]:.2f}, {target[1]:.2f}) 重复{self.repeat_count}次，标记为不可达')
                        self.failed_goals.append(target)
                        self.repeat_count = 0
                        self.last_target = None
                        return
                else:
                    self.repeat_count = 0

            self.last_target = target
            self.nav_count += 1
            self.get_logger().info(
                f'[{self.nav_count}] 发现 {len(frontiers)} 个frontier | '
                f'目标: ({target[0]:.2f}, {target[1]:.2f}) | '
                f'距离: {self.distance_to(target[0], target[1]):.2f}m')
            self.navigate_to_frontier(target[0], target[1])

    def find_frontiers(self):
        """
        前沿探索核心算法（numpy优化版）：
        Frontier = 已知空闲区域 和 未知区域 的边界
        - 空闲区域: occupancy value = 0
        - 未知区域: occupancy value = -1
        - 障碍物: occupancy value = 100
        """
        if self.map_data is None or self.map_info is None:
            return []

        height, width = self.map_data.shape

        # 使用numpy向量化找frontier cells
        free_mask = (self.map_data == 0)

        # 检查四邻域是否有未知格子
        unknown_neighbor = np.zeros((height, width), dtype=bool)
        unknown_neighbor[1:, :] |= (self.map_data[:-1, :] == -1)  # 上
        unknown_neighbor[:-1, :] |= (self.map_data[1:, :] == -1)  # 下
        unknown_neighbor[:, 1:] |= (self.map_data[:, :-1] == -1)  # 左
        unknown_neighbor[:, :-1] |= (self.map_data[:, 1:] == -1)  # 右

        frontier_mask = free_mask & unknown_neighbor
        frontier_coords = np.argwhere(frontier_mask)  # (N, 2) array of [y, x]
        frontier_cells = [(int(c[0]), int(c[1])) for c in frontier_coords]

        # 将frontier单元格聚类成groups
        cell_set = set(frontier_cells)
        visited_set = set()
        frontier_groups = []

        for cell in frontier_cells:
            if cell in visited_set:
                continue

            # BFS 找连通的frontier
            group = []
            queue = deque([cell])
            visited_set.add(cell)

            while queue:
                cy, cx = queue.popleft()
                group.append((cy, cx))

                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1),
                               (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    ny, nx = cy + dy, cx + dx
                    if (ny, nx) in cell_set and (ny, nx) not in visited_set:
                        visited_set.add((ny, nx))
                        queue.append((ny, nx))

            if len(group) >= self.min_frontier_size:
                frontier_groups.append(group)

        # 计算每个frontier group的中心点（世界坐标）
        result = []
        for group in frontier_groups:
            center_y = sum(c[0] for c in group) / len(group)
            center_x = sum(c[1] for c in group) / len(group)

            # 转换为世界坐标
            world_x = self.map_info.origin.position.x + center_x * self.map_info.resolution
            world_y = self.map_info.origin.position.y + center_y * self.map_info.resolution

            # 过滤掉之前失败过的目标附近
            skip = False
            for fx, fy in self.failed_goals:
                if math.sqrt((world_x - fx)**2 + (world_y - fy)**2) < 1.5:
                    skip = True
                    break

            if not skip:
                result.append((world_x, world_y, len(group)))

        return result

    def select_best_frontier(self, frontiers):
        """选择最佳frontier：权衡距离、大小和方向多样性"""
        if not frontiers:
            return None

        # 按方向分组（4个象限）
        quadrants = {0: [], 1: [], 2: [], 3: []}  # 右上、左上、左下、右下
        for x, y, size in frontiers:
            dist = self.distance_to(x, y)
            if dist < 0.3 or dist > 8.0:
                continue
            # 确定象限
            dx = x - self.robot_x
            dy = y - self.robot_y
            if dx >= 0 and dy >= 0:
                q = 0
            elif dx < 0 and dy >= 0:
                q = 1
            elif dx < 0 and dy < 0:
                q = 2
            else:
                q = 3
            quadrants[q].append((x, y, size, dist))

        # 计算每个象限的探索次数
        if not hasattr(self, 'quadrant_visits'):
            self.quadrant_visits = {0: 0, 1: 0, 2: 0, 3: 0}

        best_score = float('-inf')
        best_target = None
        best_quadrant = None

        for q, targets in quadrants.items():
            for x, y, size, dist in targets:
                # 基础评分 = size / distance
                base_score = size / (dist + 0.5)
                # 方向多样性奖励：访问次数少的象限得分更高
                diversity_bonus = 10.0 / (self.quadrant_visits[q] + 1)
                score = base_score + diversity_bonus

                if score > best_score:
                    best_score = score
                    best_target = (x, y)
                    best_quadrant = q

        # 记录选中的象限
        if best_quadrant is not None:
            self.quadrant_visits[best_quadrant] += 1

        return best_target

    def distance_to(self, x, y):
        """计算到目标的距离"""
        return math.sqrt((self.robot_x - x)**2 + (self.robot_y - y)**2)

    def navigate_to_frontier(self, x, y):
        """导航到frontier"""
        self.navigating = True

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation.w = 1.0

        future = self.nav_client.send_goal_async(goal_msg)
        future.add_done_callback(
            lambda f: self.nav_response_callback(f, x, y))

        # 超时保护
        self.nav_timeout_timer = self.create_timer(
            self.nav_timeout, lambda: self.cancel_navigation(x, y))

    def nav_response_callback(self, future, target_x, target_y):
        """导航响应"""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn(f'导航目标被拒绝: ({target_x:.2f}, {target_y:.2f})')
            self.failed_goals.append((target_x, target_y))
            self.navigating = False
            return

        self.nav_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda f: self.nav_result_callback(f, target_x, target_y))

    def nav_result_callback(self, future, target_x, target_y):
        """导航完成后原地旋转扫描"""
        if hasattr(self, 'nav_timeout_timer'):
            self.nav_timeout_timer.cancel()

        self.nav_goal_handle = None
        self.get_logger().info(f'导航完成 -> ({target_x:.2f}, {target_y:.2f}), 原地扫描...')

        # 到达目标后原地旋转一圈进行扫描
        twist = Twist()
        twist.angular.z = 1.0
        self.cmd_vel_pub.publish(twist)

        # 3秒后停止旋转并继续探索
        self.scan_timer = self.create_timer(3.0, self._stop_scan_spin)

    def _stop_scan_spin(self):
        """停止扫描旋转"""
        if self.scan_timer:
            self.scan_timer.cancel()
            self.scan_timer = None
        self.cmd_vel_pub.publish(Twist())
        self.navigating = False

    def cancel_navigation(self, target_x, target_y):
        """取消超时的导航"""
        if self.nav_goal_handle:
            self.get_logger().warn(f'导航超时，取消: ({target_x:.2f}, {target_y:.2f})')
            self.nav_goal_handle.cancel_goal_async()
            self.failed_goals.append((target_x, target_y))

        self.navigating = False
        self.nav_goal_handle = None

        if hasattr(self, 'nav_timeout_timer'):
            self.nav_timeout_timer.cancel()

    def finish_exploration(self):
        """完成探索，返回起点后保存地图"""
        self.exploring = False
        self.navigating = False

        if hasattr(self, 'exploration_timer'):
            self.exploration_timer.cancel()
            self.exploration_timer = None

        # 停止机器人
        self.cmd_vel_pub.publish(Twist())

        # 计算统计
        elapsed = time.time() - self.start_time if self.start_time else 0
        self.get_logger().info(f'=== 探索完成! 用时: {elapsed:.0f}秒, 导航{self.nav_count}次 ===')

        # 返回起点进行最终回环闭合
        dist_to_origin = self.distance_to(self.origin_x, self.origin_y)
        if dist_to_origin > 0.5:
            self.get_logger().info(f'返回起点进行最终回环闭合 (距离: {dist_to_origin:.2f}m)...')
            self._return_and_save()
        else:
            self.save_map()

    def _return_and_save(self):
        """返回起点后保存地图"""
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = self.origin_x
        goal_msg.pose.pose.position.y = self.origin_y
        goal_msg.pose.pose.orientation.w = 1.0

        future = self.nav_client.send_goal_async(goal_msg)
        future.add_done_callback(self._return_response_callback)

        # 回起点超时60秒
        self.return_timeout = self.create_timer(60.0, self._return_timeout)

    def _return_response_callback(self, future):
        """回起点导航响应"""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('回起点导航被拒绝，直接保存地图')
            self.save_map()
            return
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._return_done_callback)

    def _return_done_callback(self, future):
        """回到起点后保存地图"""
        if hasattr(self, 'return_timeout'):
            self.return_timeout.cancel()
        self.get_logger().info('已回到起点，SLAM回环闭合完成')
        self.save_map()

    def _return_timeout(self):
        """回起点超时"""
        if hasattr(self, 'return_timeout'):
            self.return_timeout.cancel()
        self.get_logger().warn('回起点超时，直接保存地图')
        self.save_map()

    def save_map(self):
        """保存地图"""
        map_dir = os.path.dirname(self.map_save_path)
        os.makedirs(map_dir, exist_ok=True)

        self.get_logger().info('正在保存地图...')

        try:
            cmd = [
                'ros2', 'run', 'nav2_map_server', 'map_saver_cli',
                '-f', self.map_save_path,
                '--ros-args', '-p', 'use_sim_time:=true'
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self.get_logger().info('地图保存成功!')
                self.get_logger().info(f'  PGM: {self.map_save_path}.pgm')
                self.get_logger().info(f'  YAML: {self.map_save_path}.yaml')
            else:
                self.get_logger().error(f'保存失败: {result.stderr}')
        except Exception as e:
            self.get_logger().error(f'保存地图出错: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = AutoMappingNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Ctrl+C 收到，保存地图...')
        node.finish_exploration()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
