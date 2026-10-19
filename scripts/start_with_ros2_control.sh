#!/bin/bash
# TbbRobot 一键启动脚本 (ros2_control 版本)
# 在 Ubuntu-22.04 WSL 中运行

echo "=========================================="
echo "  TbbRobot 配电室巡检机器人 启动脚本"
echo "  (使用 ros2_control 升降杆控制)"
echo "=========================================="

# 设置环境
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:/mnt/d/TbbRobot/models:$GAZEBO_MODEL_PATH

# 检查 ros2_control 包是否安装
if ! ros2 pkg list | grep -q "ros2_control"; then
    echo ""
    echo "[警告] ros2_control 未安装，正在安装..."
    sudo apt update
    sudo apt install -y ros-humble-ros2-control ros-humble-ros2-controllers ros-humble-gazebo-ros2-control
fi

echo ""
echo "[1/9] 启动 Gazebo 仿真服务器..."
ros2 launch gazebo_ros gzserver.launch.py world:=/mnt/d/TbbRobot/worlds/power_room.world &
GZSERVER_PID=$!
sleep 5

echo "[2/9] 启动 Gazebo GUI..."
gzclient &
GZCLIENT_PID=$!
sleep 3

echo "[3/9] 发布机器人描述 (URDF with ros2_control)..."
ros2 run robot_state_publisher robot_state_publisher \
    --ros-args -p robot_description:="$(cat /mnt/d/TbbRobot/models/turtlebot3_custom/lift_system.urdf)" \
    -p use_sim_time:=true &
RSP_PID=$!
sleep 2

echo "[4/9] 生成机器人模型..."
ros2 run gazebo_ros spawn_entity.py -file /mnt/d/TbbRobot/models/turtlebot3_custom/model.sdf -entity turtlebot3 -x 0 -y 0 -z 0.01
sleep 3

echo "[5/9] 启动 ros2_control 控制器..."
# 等待 controller_manager 就绪
sleep 3

# 加载 joint_state_broadcaster
echo "      加载 joint_state_broadcaster..."
ros2 control load_controller --set-state active joint_state_broadcaster 2>/dev/null || echo "      (可能已加载)"
sleep 1

# 加载 lift_controller
echo "      加载 lift_controller..."
ros2 control load_controller --set-state active lift_controller 2>/dev/null || echo "      (可能已加载)"
sleep 2

echo "[6/9] 启动 AMCL 定位..."
ros2 launch nav2_bringup localization_launch.py use_sim_time:=true map:=/mnt/d/TbbRobot/maps/power_room.yaml &
AMCL_PID=$!
sleep 5

# 激活 AMCL lifecycle
echo "      激活 AMCL..."
ros2 lifecycle set /map_server activate 2>/dev/null
ros2 lifecycle set /amcl activate 2>/dev/null
sleep 2

echo "[7/9] 启动 Nav2 导航..."
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true &
NAV2_PID=$!
sleep 5

echo "[8/9] 启动 Rosbridge WebSocket..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
ROSBRIDGE_PID=$!
sleep 2

echo "[8/9] 启动 Web Video Server..."
ros2 run web_video_server web_video_server &
WEBVIDEO_PID=$!
sleep 2

echo "[9/9] 发布初始位姿..."
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
echo "ros2_control 控制器状态:"
ros2 control list_controllers 2>/dev/null || echo "  (等待控制器加载...)"
echo ""
echo "服务端口:"
echo "  - Rosbridge:      ws://localhost:9090"
echo "  - Video Server:   http://localhost:8080"
echo ""
echo "升降杆控制话题:"
echo "  - 命令: /lift_controller/joint_trajectory"
echo "  - 状态: /joint_states"
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
