#!/bin/bash
# TbbRobot 一键启动脚本
# 在 Ubuntu-22.04 WSL 中运行

echo "=========================================="
echo "  TbbRobot 配电室巡检机器人 启动脚本"
echo "=========================================="

# 设置环境
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:/mnt/d/TbbRobot/models:$GAZEBO_MODEL_PATH

echo ""
echo "[1/8] 启动 Gazebo 仿真服务器..."
ros2 launch gazebo_ros gzserver.launch.py world:=/mnt/d/TbbRobot/worlds/power_room.world &
GZSERVER_PID=$!
sleep 5

echo "[2/8] 启动 Gazebo GUI..."
gzclient &
GZCLIENT_PID=$!
sleep 3

echo "[3/8] 生成机器人模型..."
ros2 run gazebo_ros spawn_entity.py -file /mnt/d/TbbRobot/models/turtlebot3_custom/model.sdf -entity turtlebot3 -x 0 -y 0 -z 0.01
sleep 2

echo "[4/8] 启动 Robot State Publisher..."
ros2 launch turtlebot3_gazebo robot_state_publisher.launch.py use_sim_time:=true &
RSP_PID=$!
sleep 3

echo "[5/8] 启动 AMCL 定位..."
ros2 launch nav2_bringup localization_launch.py use_sim_time:=true map:=/mnt/d/TbbRobot/maps/power_room.yaml &
AMCL_PID=$!
sleep 5

# 激活 AMCL lifecycle
echo "      激活 AMCL..."
ros2 lifecycle set /map_server activate 2>/dev/null
ros2 lifecycle set /amcl activate 2>/dev/null
sleep 2

echo "[6/8] 启动 Nav2 导航..."
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true &
NAV2_PID=$!
sleep 5

echo "[7/8] 启动 Rosbridge WebSocket..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
ROSBRIDGE_PID=$!
sleep 2

echo "[7/8] 启动 Web Video Server..."
ros2 run web_video_server web_video_server &
WEBVIDEO_PID=$!
sleep 2

echo "[8/8] 发布初始位姿..."
ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped "{
  header: {frame_id: 'map'},
  pose: {
    pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}},
    covariance: [0.25, 0, 0, 0, 0, 0, 0, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0685]
  }
}"

echo ""
echo "=========================================="
echo "  所有服务已启动!"
echo "=========================================="
echo ""
echo "服务端口:"
echo "  - Rosbridge:      ws://localhost:9090"
echo "  - Video Server:   http://localhost:8080"
echo ""
echo "下一步: 在 Windows PowerShell 中运行:"
echo "  cd d:\\TbbRobot\\web"
echo "  python -m http.server 8888"
echo ""
echo "然后打开浏览器访问: http://localhost:8888"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待任意进程结束
wait
