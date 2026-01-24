#!/bin/bash
# ROS2 服务启动脚本
# 在 Ubuntu-22.04 WSL 中运行

source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:$GAZEBO_MODEL_PATH

echo "Starting ROS2 services..."

# 启动 AMCL 定位
echo "Starting AMCL..."
ros2 launch nav2_bringup localization_launch.py use_sim_time:=true map:=/mnt/d/TbbRobot/maps/power_room.yaml &
AMCL_PID=$!
sleep 5

# 启动 Nav2 导航
echo "Starting Nav2..."
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true &
NAV2_PID=$!
sleep 5

# 启动 robot_state_publisher
echo "Starting robot_state_publisher..."
ros2 launch turtlebot3_gazebo robot_state_publisher.launch.py use_sim_time:=true &
RSP_PID=$!
sleep 3

# 启动 rosbridge
echo "Starting rosbridge..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
ROSBRIDGE_PID=$!
sleep 3

# 启动 web_video_server
echo "Starting web_video_server..."
ros2 run web_video_server web_video_server &
WEB_VIDEO_PID=$!
sleep 2

echo ""
echo "All services started:"
echo "  AMCL PID: $AMCL_PID"
echo "  Nav2 PID: $NAV2_PID"
echo "  RSP PID: $RSP_PID"
echo "  Rosbridge PID: $ROSBRIDGE_PID"
echo "  Web Video PID: $WEB_VIDEO_PID"
echo ""
echo "Press Ctrl+C to stop all services"

# 等待任意进程结束
wait
