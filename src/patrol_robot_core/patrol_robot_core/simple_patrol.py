#!/usr/bin/env python3
"""
Simple Patrol Node - Waypoint navigation with photo capture
Works with ROS2 Jazzy and Gazebo Sim
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, LaserScan
from cv_bridge import CvBridge
import cv2
import os
import time
import math
from datetime import datetime


class SimplePatrolNode(Node):
    """
    A simplified patrol node that navigates to waypoints and captures images.
    Uses direct velocity commands instead of Nav2 for simplicity.
    """

    def __init__(self):
        super().__init__('simple_patrol_node')

        # Parameters
        self.declare_parameter('output_dir', '/tmp/patrol_images')
        self.declare_parameter('linear_speed', 0.3)
        self.declare_parameter('angular_speed', 0.5)
        self.declare_parameter('obstacle_distance', 0.5)  # meters to trigger avoidance
        self.declare_parameter('obstacle_slow_distance', 1.0)  # meters to start slowing

        self.output_dir = self.get_parameter('output_dir').get_parameter_value().string_value
        self.linear_speed = self.get_parameter('linear_speed').get_parameter_value().double_value
        self.angular_speed = self.get_parameter('angular_speed').get_parameter_value().double_value
        self.obstacle_distance = self.get_parameter('obstacle_distance').get_parameter_value().double_value
        self.obstacle_slow_distance = self.get_parameter('obstacle_slow_distance').get_parameter_value().double_value

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Publishers and Subscribers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)
        self.image_sub = self.create_subscription(
            Image, '/camera_sensor/image_raw', self.image_callback, 10)
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)

        # Obstacle avoidance state
        self.front_min_dist = float('inf')  # Minimum distance in front sector
        self.left_min_dist = float('inf')   # Minimum distance on left
        self.right_min_dist = float('inf')  # Minimum distance on right
        self.obstacle_detected = False
        self.avoidance_direction = 0  # -1 = turn right, 1 = turn left

        # State
        self.latest_image = None
        self.bridge = CvBridge()
        self.current_pose = None  # (x, y, yaw)
        self.initial_odom = None  # Store first odom to use as origin
        self.current_waypoint_idx = 0
        self.is_navigating = False

        # Define patrol waypoints (x, y, yaw in radians)
        # Room is 10x10m (-5 to 5), interior walls at (-2,2) horizontal and (2,-1) vertical
        # Keep waypoints away from walls with clearance
        self.waypoints = [
            (0.0, -3.0, 0.0),        # South corridor
            (3.5, -3.0, math.pi/2),   # Southeast area
            (3.5, 3.0, math.pi),      # Northeast area
            (-3.5, 3.5, -math.pi/2),  # Northwest area
        ]

        # Timer for patrol loop
        self.patrol_timer = self.create_timer(0.1, self.patrol_loop)
        self.state = 'idle'
        self.target_pose = None
        self.state_start_time = None

        self.get_logger().info(f'Simple Patrol Node initialized. Output dir: {self.output_dir}')
        self.get_logger().info(f'Patrol waypoints: {len(self.waypoints)} points')

        # Start patrol after a delay
        self.create_timer(3.0, self.start_patrol, callback_group=None)

    def start_patrol(self):
        """Start the patrol sequence"""
        if self.state == 'idle':
            self.get_logger().info('Starting patrol...')
            self.state = 'navigate'
            self.target_pose = self.waypoints[self.current_waypoint_idx]
            self.get_logger().info(f'Navigating to waypoint {self.current_waypoint_idx + 1}: {self.target_pose}')

    def odom_callback(self, msg):
        """Update current pose from odometry"""
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                       1.0 - 2.0 * (q.y * q.y + q.z * q.z))

        # Use first odom reading as origin
        if self.initial_odom is None:
            self.initial_odom = (x, y, yaw)
            self.get_logger().info(f'Initial odom set: x={x:.2f}, y={y:.2f}, yaw={yaw:.2f}')

        # Compute relative position from start
        ox, oy, _ = self.initial_odom
        self.current_pose = (x - ox, y - oy, yaw)

    def scan_callback(self, msg):
        """Process laser scan for obstacle detection"""
        ranges = msg.ranges
        num_ranges = len(ranges)
        if num_ranges == 0:
            return

        # Divide scan into sectors (assuming 360-degree lidar)
        # Front: -30 to +30 degrees
        # Left: +30 to +90 degrees
        # Right: -90 to -30 degrees
        sector_size = num_ranges // 12  # 30 degrees each

        # Front sector (indices around 0 for front-facing lidar)
        front_indices = list(range(0, sector_size)) + list(range(num_ranges - sector_size, num_ranges))
        left_indices = list(range(sector_size, sector_size * 3))
        right_indices = list(range(num_ranges - sector_size * 3, num_ranges - sector_size))

        def min_valid(indices):
            valid = [ranges[i] for i in indices
                     if i < num_ranges and msg.range_min < ranges[i] < msg.range_max]
            return min(valid) if valid else float('inf')

        self.front_min_dist = min_valid(front_indices)
        self.left_min_dist = min_valid(left_indices)
        self.right_min_dist = min_valid(right_indices)

        # Determine if obstacle is too close in front
        self.obstacle_detected = self.front_min_dist < self.obstacle_distance

        # Choose avoidance direction: turn away from the closer side
        if self.obstacle_detected:
            if self.left_min_dist > self.right_min_dist:
                self.avoidance_direction = 1  # Turn left (more space on left)
            else:
                self.avoidance_direction = -1  # Turn right (more space on right)

    def image_callback(self, msg):
        """Store the latest image"""
        self.latest_image = msg

    def get_current_pose(self):
        """Get current robot pose from odometry"""
        return self.current_pose

    def capture_image(self):
        """Capture and save the current image"""
        if self.latest_image is None:
            self.get_logger().warn('No image available to capture')
            return False

        try:
            cv_image = self.bridge.imgmsg_to_cv2(self.latest_image, 'bgr8')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'patrol_wp{self.current_waypoint_idx + 1}_{timestamp}.jpg'
            filepath = os.path.join(self.output_dir, filename)
            cv2.imwrite(filepath, cv_image)
            self.get_logger().info(f'Image saved: {filepath}')
            return True
        except Exception as e:
            self.get_logger().error(f'Failed to capture image: {e}')
            return False

    def patrol_loop(self):
        """Main patrol state machine"""
        if self.state == 'idle':
            return

        current_pose = self.get_current_pose()
        if current_pose is None:
            return

        cmd = Twist()

        if self.state == 'navigate':
            if self.target_pose is None:
                return

            # Calculate distance and angle to target
            dx = self.target_pose[0] - current_pose[0]
            dy = self.target_pose[1] - current_pose[1]
            distance = math.sqrt(dx * dx + dy * dy)
            target_angle = math.atan2(dy, dx)
            angle_diff = self.normalize_angle(target_angle - current_pose[2])

            # Check if arrived
            if distance < 0.3:
                self.get_logger().info(f'Arrived at waypoint {self.current_waypoint_idx + 1}')
                self.state = 'rotate_final'
                self.state_start_time = time.time()
                cmd.linear.x = 0.0
                cmd.angular.z = 0.0
            # Obstacle avoidance takes priority
            elif self.obstacle_detected:
                # Stop forward motion and turn to avoid
                cmd.linear.x = 0.0
                cmd.angular.z = self.angular_speed * self.avoidance_direction
            # First rotate towards target
            elif abs(angle_diff) > 0.2:
                cmd.angular.z = self.angular_speed if angle_diff > 0 else -self.angular_speed
            # Move forward with obstacle-aware speed control
            else:
                # Slow down when approaching obstacles
                if self.front_min_dist < self.obstacle_slow_distance:
                    speed_factor = max(0.3, (self.front_min_dist - self.obstacle_distance) /
                                       (self.obstacle_slow_distance - self.obstacle_distance))
                    cmd.linear.x = self.linear_speed * speed_factor
                else:
                    cmd.linear.x = self.linear_speed
                cmd.angular.z = angle_diff * 0.5  # Small correction

        elif self.state == 'rotate_final':
            # Rotate to final orientation
            target_yaw = self.target_pose[2]
            angle_diff = self.normalize_angle(target_yaw - current_pose[2])

            if abs(angle_diff) < 0.1 or time.time() - self.state_start_time > 5.0:
                self.state = 'capture'
                self.state_start_time = time.time()
                cmd.angular.z = 0.0
            else:
                cmd.angular.z = self.angular_speed * 0.5 if angle_diff > 0 else -self.angular_speed * 0.5

        elif self.state == 'capture':
            # Wait a moment and capture image
            if time.time() - self.state_start_time > 1.0:
                self.capture_image()
                self.state = 'next_waypoint'
                self.state_start_time = time.time()

        elif self.state == 'next_waypoint':
            # Wait and move to next waypoint
            if time.time() - self.state_start_time > 2.0:
                self.current_waypoint_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
                self.target_pose = self.waypoints[self.current_waypoint_idx]
                self.get_logger().info(f'Moving to waypoint {self.current_waypoint_idx + 1}: {self.target_pose}')
                self.state = 'navigate'

        self.cmd_vel_pub.publish(cmd)

    def normalize_angle(self, angle):
        """Normalize angle to [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle


def main(args=None):
    rclpy.init(args=args)
    node = SimplePatrolNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down...')
    finally:
        # Stop the robot
        cmd = Twist()
        node.cmd_vel_pub.publish(cmd)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
