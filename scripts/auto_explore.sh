#!/bin/bash
# 自动探索建图脚本
# 像扫地机器人一样自动寻路建图

set -e

# Source ROS2 环境
source /opt/ros/jazzy/setup.bash
source /mnt/d/TbbRobot/install/setup.bash
source /mnt/d/TbbRobot/m-explore-ros2-main/m-explore-ros2-main/install/setup.bash

echo "=================================="
echo "  自动探索建图系统"
echo "  机器人将像扫地机器人一样自动探索"
echo "=================================="

# 启动基础系统 (Gazebo + Nav2 + SLAM + RViz)
echo "[1/2] 启动 Gazebo + Nav2 + SLAM..."
ros2 launch patrol_robot_navigation auto_explore.launch.py &
BASE_PID=$!

# 等待系统完全启动
echo "等待系统启动 (30秒)..."
sleep 30

# 检查 Nav2 是否就绪
echo "[2/2] 启动自动探索 (explore_lite)..."

# 启动 explore_lite 自动探索
ros2 run explore_lite explore --ros-args \
    -p robot_base_frame:=base_footprint \
    -p costmap_topic:=map \
    -p costmap_updates_topic:=map_updates \
    -p visualize:=true \
    -p planner_frequency:=0.33 \
    -p progress_timeout:=60.0 \
    -p potential_scale:=3.0 \
    -p gain_scale:=1.0 \
    -p min_frontier_size:=0.5 \
    -p use_sim_time:=true \
    -p return_to_init:=true &
EXPLORE_PID=$!

echo ""
echo "=================================="
echo "  自动探索已启动!"
echo "  - 基础系统 PID: $BASE_PID"
echo "  - 探索节点 PID: $EXPLORE_PID"
echo "  按 Ctrl+C 停止"
echo "=================================="

# 等待任一进程结束
wait -n $BASE_PID $EXPLORE_PID

# 清理
echo "正在停止..."
kill $BASE_PID 2>/dev/null || true
kill $EXPLORE_PID 2>/dev/null || true
echo "已停止"
