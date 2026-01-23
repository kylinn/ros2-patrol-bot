#!/usr/bin/env python3
"""
Patrol Node - Based on fishros/ros2_patrol_robot
Adapted for ROS2 Jazzy + Gazebo Sim (Harmonic)
Uses Nav2 for navigation with full obstacle avoidance
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
import time
import math
import threading
from datetime import datetime

# TF2 for getting robot pose
import tf2_ros
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from rclpy.duration import Duration

from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult


class PatrolNode(BasicNavigator):
    """
    Patrol node based on the open source fishros/ros2_patrol_robot.
    Uses Nav2 BasicNavigator for navigation with automatic obstacle avoidance.
    """

    def __init__(self):
        super().__init__('patrol_node')

        # --- TF ---
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # --- Image handling ---
        self.latest_image = None
        self.image_lock = threading.Lock()
        self.bridge = CvBridge()
        self.image_subscriber = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)

        # --- Parameters ---
        self.declare_parameter('initial_pose.x', 0.0)
        self.declare_parameter('initial_pose.y', 0.0)
        self.declare_parameter('initial_pose.yaw', 0.0)
        self.declare_parameter('patrol_points', rclpy.Parameter.Type.STRING_ARRAY)
        self.declare_parameter('output_dir', '/tmp/patrol_images')
        self.declare_parameter('loop_patrol', True)

        self.output_dir = self.get_parameter('output_dir').get_parameter_value().string_value
        self.loop_patrol = self.get_parameter('loop_patrol').get_parameter_value().bool_value
        os.makedirs(self.output_dir, exist_ok=True)

        self.get_logger().info("Patrol node initialized.")

    def image_callback(self, msg: Image):
        """Store the latest image frame"""
        with self.image_lock:
            self.latest_image = msg

    def record_image(self, waypoint_idx: int):
        """Capture and save current camera image"""
        with self.image_lock:
            if self.latest_image is None:
                self.get_logger().warn('No image available to capture')
                return False

            try:
                cv_image = self.bridge.imgmsg_to_cv2(self.latest_image, 'bgr8')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'patrol_wp{waypoint_idx + 1}_{timestamp}.jpg'
                filepath = os.path.join(self.output_dir, filename)
                cv2.imwrite(filepath, cv_image)
                self.get_logger().info(f'Image saved: {filepath}')
                return True
            except Exception as e:
                self.get_logger().error(f'Failed to capture image: {e}')
                return False

    def get_pose_by_xyyaw(self, x: float, y: float, yaw: float) -> PoseStamped:
        """Create PoseStamped from x, y, yaw (radians)"""
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
        # Quaternion from yaw
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def init_robot_pose(self):
        """Set initial robot pose from parameters"""
        self.get_logger().info("Setting initial robot pose...")
        init_x = self.get_parameter('initial_pose.x').get_parameter_value().double_value
        init_y = self.get_parameter('initial_pose.y').get_parameter_value().double_value
        init_yaw = self.get_parameter('initial_pose.yaw').get_parameter_value().double_value

        initial_pose = self.get_pose_by_xyyaw(init_x, init_y, init_yaw)
        self.setInitialPose(initial_pose)
        self.get_logger().info(
            f"Initial pose set: x={init_x}, y={init_y}, yaw={init_yaw}")

    def get_target_points(self) -> list:
        """Parse patrol points from parameters (format: 'x,y,yaw_degrees')"""
        self.get_logger().info("Loading patrol points from parameters...")
        point_strings = self.get_parameter(
            'patrol_points').get_parameter_value().string_array_value

        if not point_strings:
            self.get_logger().error("Parameter 'patrol_points' is empty!")
            return []

        target_poses = []
        for point_str in point_strings:
            try:
                parts = point_str.split(',')
                x = float(parts[0])
                y = float(parts[1])
                yaw_degrees = float(parts[2])
                yaw_radians = math.radians(yaw_degrees)
                pose = self.get_pose_by_xyyaw(x, y, yaw_radians)
                target_poses.append(pose)
                self.get_logger().info(
                    f"  Waypoint added: x={x}, y={y}, yaw={yaw_degrees} deg")
            except (ValueError, IndexError) as e:
                self.get_logger().warn(
                    f"Failed to parse point '{point_str}': {e}")

        return target_poses

    def nav_to_pose(self, target_pose: PoseStamped) -> bool:
        """Navigate to target pose using Nav2 with feedback"""
        x = target_pose.pose.position.x
        y = target_pose.pose.position.y
        self.get_logger().info(f"Navigating to: ({x:.2f}, {y:.2f})")
        self.goToPose(target_pose)

        while not self.isTaskComplete():
            feedback = self.getFeedback()
            current_pose = self.get_current_pose()

            if feedback and current_pose:
                distance_remaining = feedback.distance_remaining
                pos_x = current_pose.pose.position.x
                pos_y = current_pose.pose.position.y
                self.get_logger().info(
                    f'  Position: ({pos_x:.2f}, {pos_y:.2f}) | '
                    f'Remaining: {distance_remaining:.2f}m')

            time.sleep(1)

        result = self.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info('Navigation succeeded!')
            return True
        elif result == TaskResult.CANCELED:
            self.get_logger().warn('Navigation was canceled!')
            return False
        elif result == TaskResult.FAILED:
            self.get_logger().error('Navigation failed!')
            return False
        else:
            self.get_logger().error(f'Unknown navigation result: {result}')
            return False

    def get_current_pose(self) -> PoseStamped:
        """Get current robot pose from TF"""
        try:
            transform = self.tf_buffer.lookup_transform(
                'map', 'base_footprint',
                rclpy.time.Time(),
                timeout=Duration(seconds=1.0))

            pose = PoseStamped()
            pose.header.frame_id = 'map'
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = transform.transform.translation.x
            pose.pose.position.y = transform.transform.translation.y
            pose.pose.position.z = transform.transform.translation.z
            pose.pose.orientation = transform.transform.rotation
            return pose
        except Exception as e:
            self.get_logger().debug(f"Cannot get pose from TF: {e}")
            return None

    def patrol_loop(self):
        """Main patrol logic"""
        # 1. Wait for Nav2 to become active
        # Note: localizer='slam_toolbox' skips AMCL check since we use SLAM for localization
        self.get_logger().info("Waiting for Nav2 to become active...")
        self.waitUntilNav2Active(localizer='slam_toolbox')
        self.get_logger().info("Nav2 is active! Starting patrol.")

        # 2. Set initial pose
        self.init_robot_pose()
        time.sleep(2)  # Wait for localization to converge

        # 3. Get patrol points
        patrol_points = self.get_target_points()
        if not patrol_points:
            self.get_logger().error("No patrol points available. Exiting.")
            return

        # 4. Start patrol loop
        point_index = 0
        self.get_logger().info("=== Patrol task started ===")

        while rclpy.ok():
            target_pose = patrol_points[point_index]
            self.get_logger().info(
                f"--- Heading to waypoint {point_index + 1}/{len(patrol_points)} ---")

            nav_success = self.nav_to_pose(target_pose)

            if nav_success:
                self.get_logger().info("Arrived! Capturing image...")
                time.sleep(2)  # Wait for robot to stabilize
                self.record_image(point_index)
                time.sleep(1)
            else:
                self.get_logger().warn(
                    "Navigation failed. Retrying in 30 seconds...")
                time.sleep(30)
                continue  # Retry current waypoint

            # Move to next waypoint
            point_index = (point_index + 1) % len(patrol_points)

            if point_index == 0 and not self.loop_patrol:
                self.get_logger().info("=== Patrol complete ===")
                break

            time.sleep(3)  # Brief pause between waypoints


def main(args=None):
    rclpy.init(args=args)
    patrol_node = PatrolNode()

    try:
        patrol_node.patrol_loop()
    except KeyboardInterrupt:
        patrol_node.get_logger().info('Shutting down patrol node...')
    finally:
        patrol_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
