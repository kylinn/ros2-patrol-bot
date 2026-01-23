#!/bin/bash
# ROS2 Jazzy 安装脚本 (Ubuntu 24.04)
set -e

echo "=========================================="
echo "  ROS2 Jazzy 安装脚本"
echo "=========================================="

# 1. 设置 locale
echo "[1/7] 设置 locale..."
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# 2. 添加 ROS2 apt 仓库
echo "[2/7] 添加 ROS2 仓库..."
sudo apt install -y software-properties-common curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 3. 安装 ROS2 Jazzy
echo "[3/7] 安装 ROS2 Jazzy Desktop..."
sudo apt update
sudo apt install -y ros-jazzy-desktop

# 4. 安装开发工具
echo "[4/7] 安装开发工具..."
sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-argcomplete

# 5. 安装 Gazebo 和仿真相关包
echo "[5/7] 安装 Gazebo 仿真环境..."
sudo apt install -y ros-jazzy-gazebo-ros-pkgs ros-jazzy-gazebo-ros

# 6. 安装 Nav2 导航包
echo "[6/7] 安装 Nav2 导航包..."
sudo apt install -y ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox

# 7. 安装其他依赖
echo "[7/7] 安装其他依赖..."
sudo apt install -y ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher-gui ros-jazzy-teleop-twist-keyboard

# 初始化 rosdep
echo "初始化 rosdep..."
sudo rosdep init 2>/dev/null || true
rosdep update

# 添加 source 到 bashrc
echo "配置环境变量..."
echo "" >> ~/.bashrc
echo "# ROS2 Jazzy" >> ~/.bashrc
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc

echo "=========================================="
echo "  ROS2 Jazzy 安装完成！"
echo "=========================================="
echo ""
echo "请运行以下命令激活环境："
echo "  source /opt/ros/jazzy/setup.bash"
echo ""
