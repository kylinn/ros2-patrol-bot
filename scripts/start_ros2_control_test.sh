#!/bin/bash
# 升降杆 ros2_control 测试启动脚本

set -e

echo "=========================================="
echo "  升降杆 ros2_control 测试"
echo "=========================================="

source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:/mnt/d/TbbRobot/models:$GAZEBO_MODEL_PATH

echo ""
echo "[1/5] 启动 Gazebo 服务器..."
ros2 launch gazebo_ros gzserver.launch.py world:=/mnt/d/TbbRobot/worlds/power_room.world &
GZSERVER_PID=$!
sleep 8

echo "[2/5] 启动 Gazebo GUI..."
gzclient &
sleep 3

echo "[3/5] 发布 robot_description (包含 ros2_control 接口)..."
# 关键：必须在 spawn 之前发布 robot_description
ros2 run robot_state_publisher robot_state_publisher \
    --ros-args \
    -p robot_description:="$(cat /mnt/d/TbbRobot/models/turtlebot3_custom/lift_system.urdf)" \
    -p use_sim_time:=true &
RSP_PID=$!
sleep 3

# 验证 robot_description 已发布
echo "      验证 robot_description..."
ros2 param get /robot_state_publisher robot_description 2>/dev/null | head -2

echo "[4/5] 生成机器人模型..."
ros2 run gazebo_ros spawn_entity.py \
    -file /mnt/d/TbbRobot/models/turtlebot3_custom/model.sdf \
    -entity turtlebot3 \
    -x 0 -y 0 -z 0.01
sleep 5

echo "[5/5] 检查 controller_manager..."
echo "等待 controller_manager 启动..."
for i in {1..10}; do
    if ros2 service list 2>/dev/null | grep -q "/controller_manager/list_controllers"; then
        echo "controller_manager 已就绪!"
        break
    fi
    echo "  等待中... ($i/10)"
    sleep 2
done

echo ""
echo "尝试加载控制器..."
ros2 control load_controller --set-state active joint_state_broadcaster 2>&1 || echo "(跳过)"
sleep 1
ros2 control load_controller --set-state active lift_controller 2>&1 || echo "(跳过)"
sleep 1

echo ""
echo "=========================================="
echo "  当前控制器状态:"
ros2 control list_controllers 2>&1 || echo "(controller_manager 未启动)"
echo "=========================================="

echo ""
echo "话题列表 (lift 相关):"
ros2 topic list | grep -i lift || echo "(无 lift 相关话题)"

echo ""
echo "按 Ctrl+C 退出"
wait
