# ROS2 巡检机器人 - 安装与使用指南

## 目录
1. [环境要求](#环境要求)
2. [安装 WSL2 + Ubuntu](#安装-wsl2--ubuntu)
3. [安装 ROS2 Jazzy](#安装-ros2-jazzy)
4. [编译项目](#编译项目)
5. [运行仿真](#运行仿真)
6. [常用命令](#常用命令)

---

## 环境要求

- Windows 10 (版本 2004+) 或 Windows 11
- WSL2 + Ubuntu 24.04
- 8GB+ 内存
- 支持 OpenGL 的显卡

---

## 安装 WSL2 + Ubuntu

### 1. 启用 WSL2

以管理员身份打开 PowerShell，执行：

```powershell
wsl --install
```

重启电脑后，WSL2 和 Ubuntu 会自动安装。

### 2. 配置 Ubuntu

首次启动 Ubuntu 时，设置用户名和密码。

### 3. (可选) 配置免密 sudo

```bash
sudo bash -c 'echo "你的用户名 ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/nopasswd'
```

---

## 安装 ROS2 Jazzy

在 Ubuntu 终端中执行以下步骤：

### 1. 设置 locale

```bash
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
```

### 2. 添加 ROS2 软件源

```bash
sudo apt install -y software-properties-common curl

# 添加 ROS2 GPG 密钥
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# 添加软件源
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu noble main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

### 3. 安装 ROS2 Jazzy

```bash
sudo apt update
sudo apt install -y ros-jazzy-desktop
```

### 4. 安装 Gazebo 和导航包

```bash
# Gazebo Sim (新版仿真器)
sudo apt install -y ros-jazzy-ros-gz

# Nav2 导航栈
sudo apt install -y ros-jazzy-navigation2 ros-jazzy-nav2-bringup

# SLAM
sudo apt install -y ros-jazzy-slam-toolbox

# 其他工具
sudo apt install -y ros-jazzy-xacro ros-jazzy-joint-state-publisher-gui ros-jazzy-teleop-twist-keyboard

# 编译工具
sudo apt install -y python3-colcon-common-extensions python3-rosdep
```

### 5. 初始化 rosdep

```bash
sudo rosdep init
rosdep update
```

### 6. 配置环境变量

```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

## 编译项目

### 1. 进入工作空间

```bash
cd /mnt/d/TbbRobot
```

### 2. 编译

```bash
colcon build --symlink-install
```

### 3. 激活工作空间

```bash
source install/setup.bash
```

建议添加到 `~/.bashrc`：

```bash
echo "source /mnt/d/TbbRobot/install/setup.bash" >> ~/.bashrc
```

---

## 运行仿真

### 启动 Gazebo 仿真

```bash
ros2 launch patrol_robot_gazebo gazebo.launch.py
```

### 启动完整仿真 (Gazebo + SLAM + RViz)

```bash
ros2 launch patrol_robot_bringup simulation.launch.py
```

### 键盘控制机器人

在新终端中：

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

控制键：
- `i` - 前进
- `k` - 停止
- `j` - 左转
- `l` - 右转
- `,` - 后退

### 保存地图

建图完成后：

```bash
ros2 run nav2_map_server map_saver_cli -f ~/map
```

### 使用地图导航

```bash
ros2 launch patrol_robot_bringup full_navigation.launch.py map:=/home/你的用户名/map.yaml
```

---

## 常用命令

### 查看话题列表

```bash
ros2 topic list
```

### 查看话题数据

```bash
ros2 topic echo /scan        # 激光雷达数据
ros2 topic echo /odom        # 里程计数据
ros2 topic echo /cmd_vel     # 速度命令
```

### 查看 TF 树

```bash
ros2 run tf2_tools view_frames
```

### 启动 RViz

```bash
ros2 run rviz2 rviz2
```

---

## 项目结构

```
TbbRobot/
├── src/
│   ├── patrol_robot_description/   # 机器人 URDF 模型
│   │   ├── urdf/                   # Xacro 文件
│   │   ├── launch/                 # 显示启动文件
│   │   └── rviz/                   # RViz 配置
│   │
│   ├── patrol_robot_gazebo/        # Gazebo 仿真
│   │   ├── worlds/                 # 世界文件
│   │   └── launch/                 # 仿真启动文件
│   │
│   ├── patrol_robot_navigation/    # 导航配置
│   │   ├── config/                 # Nav2 和 SLAM 参数
│   │   └── launch/                 # 导航启动文件
│   │
│   └── patrol_robot_bringup/       # 综合启动文件
│       ├── launch/                 # 一键启动脚本
│       └── rviz/                   # 导航 RViz 配置
│
├── install/                        # 编译输出
├── build/                          # 编译中间文件
└── log/                            # 日志
```

---

## 故障排除

### 1. Gazebo 窗口不显示

确保 WSLg 正常工作：

```bash
echo $DISPLAY  # 应该输出 :0
```

如果没有，尝试更新 WSL：

```powershell
wsl --update
```

### 2. 编译失败

检查依赖是否安装完整：

```bash
rosdep install --from-paths src --ignore-src -r -y
```

### 3. 找不到包

确保环境已激活：

```bash
source /opt/ros/jazzy/setup.bash
source /mnt/d/TbbRobot/install/setup.bash
```

---

## 参考链接

- [ROS2 Jazzy 文档](https://docs.ros.org/en/jazzy/)
- [Nav2 导航文档](https://navigation.ros.org/)
- [Gazebo Sim 文档](https://gazebosim.org/docs)
