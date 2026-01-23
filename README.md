# ros2-patrol-bot

基于 ROS2 Jazzy 的室内巡检机器人仿真系统，支持 SLAM 建图、自主导航和多场景仿真。

## 功能特性

- **SLAM 建图** - 基于 SLAM Toolbox 的实时建图
- **自主导航** - Nav2 导航栈，支持路径规划和避障
- **多场景仿真** - 包含办公室和配电室两种环境
- **传感器仿真** - 激光雷达、IMU、RGB 相机

## 环境要求

- Ubuntu 24.04 (或 WSL2)
- ROS2 Jazzy
- Gazebo Harmonic (gz-sim8)

## 安装

```bash
# 克隆仓库
git clone https://github.com/kylinn/ros2-patrol-bot.git
cd ros2-patrol-bot

# 安装依赖
rosdep install --from-paths src --ignore-src -r -y

# 编译
colcon build --symlink-install

# 加载环境
source install/setup.bash
```

## 快速开始

### 1. 启动仿真 + SLAM 建图

```bash
# 办公室环境
ros2 launch patrol_robot_navigation auto_explore.launch.py

# 配电室环境
ros2 launch patrol_robot_navigation auto_explore.launch.py world:=power_distribution_room
```

### 2. 键盘遥控

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### 3. 自动建图

```bash
ros2 run patrol_robot_core simple_mapping --ros-args -p use_sim_time:=true
```

### 4. 保存地图

```bash
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map --ros-args -p use_sim_time:=true
```

### 5. 使用已有地图导航

```bash
ros2 launch patrol_robot_navigation navigation.launch.py map:=/path/to/map.yaml
```

## 项目结构

```
patrol-robot-ros2/
├── src/
│   ├── patrol_robot_description/   # 机器人 URDF 模型
│   ├── patrol_robot_gazebo/        # Gazebo 仿真配置
│   ├── patrol_robot_navigation/    # 导航配置和启动文件
│   └── patrol_robot_core/          # 核心功能节点
├── maps/                           # 保存的地图文件
└── README.md
```

## 软件包说明

| 包名 | 描述 |
|------|------|
| `patrol_robot_description` | 机器人 URDF/Xacro 模型定义 |
| `patrol_robot_gazebo` | Gazebo 世界文件和仿真启动 |
| `patrol_robot_navigation` | Nav2 导航配置、SLAM 参数 |
| `patrol_robot_core` | 自动建图、巡检等功能节点 |

## 仿真场景

### 办公室 (indoor_office)
- 面积：约 100 平方米
- 包含：桌椅、柜子、走廊

### 配电室 (power_distribution_room)
- 面积：约 200 平方米
- 包含：高压柜、变压器、电缆桥架

## 配置文件

- `nav2_params.yaml` - Nav2 导航参数
- `slam_params.yaml` - SLAM Toolbox 参数
- `rpp_params.yaml` - 路径跟踪控制器参数

## 常用命令

```bash
# 查看话题
ros2 topic list

# 查看 TF 树
ros2 run tf2_tools view_frames

# RViz 可视化
ros2 run rviz2 rviz2 -d src/patrol_robot_navigation/config/slam_view.rviz
```

## 已知问题

1. **SLAM 漂移** - 在大面积或特征稀疏区域，建图可能出现漂移
2. **仿真性能** - 复杂场景下 Gazebo 可能较慢

## 许可证

MIT License

## 参考

- [ROS2 Jazzy 文档](https://docs.ros.org/en/jazzy/)
- [Nav2 导航栈](https://docs.nav2.org/)
- [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox)
- [Gazebo Sim](https://gazebosim.org/)
