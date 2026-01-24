#!/usr/bin/env python3
"""Auto-explore script: drives robot in a lawn-mower pattern to build SLAM map."""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
import math
import time

class AutoExplorer(Node):
    def __init__(self):
        super().__init__('auto_explorer')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        self.timer = self.create_timer(0.1, self.control_loop)

        self.min_front = 999.0
        self.min_left = 999.0
        self.min_right = 999.0
        self.state = 'forward'
        self.turn_count = 0
        self.turn_dir = 1  # 1=left, -1=right
        self.state_time = time.time()
        self.total_start = time.time()

    def scan_cb(self, msg):
        n = len(msg.ranges)
        # Front: -30 to +30 degrees
        front_indices = list(range(0, n//12)) + list(range(11*n//12, n))
        # Left: 60-120 degrees
        left_indices = list(range(n//6, n//3))
        # Right: 240-300 degrees
        right_indices = list(range(2*n//3, 5*n//6))

        def min_valid(indices):
            vals = [msg.ranges[i] for i in indices
                    if msg.range_min < msg.ranges[i] < msg.range_max]
            return min(vals) if vals else 999.0

        self.min_front = min_valid(front_indices)
        self.min_left = min_valid(left_indices)
        self.min_right = min_valid(right_indices)

    def control_loop(self):
        twist = Twist()
        elapsed = time.time() - self.total_start

        # Stop after 120 seconds
        if elapsed > 120:
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.pub.publish(twist)
            self.get_logger().info('Exploration complete!')
            rclpy.shutdown()
            return

        state_elapsed = time.time() - self.state_time

        if self.state == 'forward':
            if self.min_front < 0.5:
                # Too close to obstacle, turn
                self.state = 'turn'
                self.state_time = time.time()
                self.turn_dir *= -1  # Alternate turn direction
                self.turn_count += 1
            else:
                twist.linear.x = 0.4
                twist.angular.z = 0.0

        elif self.state == 'turn':
            twist.linear.x = 0.0
            twist.angular.z = 0.8 * self.turn_dir
            if state_elapsed > 2.0:  # Turn for 2 seconds (~90 degrees)
                self.state = 'short_forward'
                self.state_time = time.time()

        elif self.state == 'short_forward':
            if self.min_front < 0.5:
                self.state = 'turn'
                self.state_time = time.time()
            elif state_elapsed > 3.0:
                self.state = 'turn2'
                self.state_time = time.time()
            else:
                twist.linear.x = 0.4
                twist.angular.z = 0.0

        elif self.state == 'turn2':
            twist.linear.x = 0.0
            twist.angular.z = 0.8 * self.turn_dir
            if state_elapsed > 2.0:
                self.state = 'forward'
                self.state_time = time.time()

        self.pub.publish(twist)

        if int(elapsed) % 10 == 0 and int(elapsed * 10) % 100 == 0:
            self.get_logger().info(
                f'State: {self.state}, Front: {self.min_front:.1f}m, '
                f'Turns: {self.turn_count}, Time: {int(elapsed)}s')

def main():
    rclpy.init()
    node = AutoExplorer()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
