# TbbRobot - 配电室巡检机器人仿真系统

基于 ROS2 Humble + Gazebo Classic 的配电室智能巡检机器人仿真系统，支持 Web 远程控制、自主导航、升降杆摄像和巡检点管理。

## 功能特性

- **Web 控制台** - 浏览器远程控制，无需安装客户端
- **自主导航** - Nav2 导航栈，支持路径规划和自动避障
- **升降杆机构** - 可升降摄像头支架，用于近距离拍摄仪表盘
- **巡检点管理** - 可配置巡检路线，自动执行巡检任务
- **实时视频流** - 摄像头实时画面传输到 Web 界面
- **AMCL 定位** - 基于已有地图的精确定位

## 环境要求

- Windows 11 + WSL2
- Ubuntu 22.04 (WSL)
- ROS2 Humble
- Gazebo Classic 11
- NVIDIA GPU (推荐，解决 WSLg 黑屏问题)

## 项目结构

```
TbbRobot/
├── maps/                    # 地图文件
│   ├── power_room.yaml      # 配电室地图配置
│   └── power_room.pgm       # 配电室地图图像
├── models/                  # Gazebo 模型
│   ├── turtlebot3_custom/   # 自定义机器人 (带升降杆)
│   └── cabinet/             # 配电柜模型
├── worlds/                  # Gazebo 世界文件
│   └── power_room.world     # 配电室仿真环境
├── scripts/                 # Python 脚本
│   ├── lift_position_controller.py  # 升降杆 PID 控制器
│   ├── lift_controller.py   # 升降杆简易控制
│   └── auto_explore.py      # 自动探索脚本
├── web/                     # Web 控制界面
│   └── index.html           # 巡检控制台页面
├── launch/                  # 启动脚本
└── docs/                    # 文档
```

## 快速开始

### 方法一：一键启动脚本 (推荐)

在 WSL Ubuntu-22.04 终端中运行：

```bash
# 进入 WSL
wsl -d Ubuntu-22.04

# 运行一键启动脚本
bash /mnt/d/TbbRobot/scripts/start_all.sh
```

然后在 **Windows PowerShell** 中启动 Web 服务器：

```powershell
cd d:\TbbRobot\web
python -m http.server 8888
```

最后打开浏览器访问: http://localhost:8888

---

### 方法二：手动分步启动

#### 步骤 1: 进入 WSL 并设置环境

```bash
wsl -d Ubuntu-22.04

# 设置 ROS2 环境
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:/mnt/d/TbbRobot/models:$GAZEBO_MODEL_PATH
```

#### 步骤 2: 启动 Gazebo 仿真

```bash
# 启动 gzserver (仿真服务器)
ros2 launch gazebo_ros gzserver.launch.py world:=/mnt/d/TbbRobot/worlds/power_room.world &
sleep 5

# 启动 gzclient (GUI 界面)
gzclient &
sleep 3

# 生成机器人模型
ros2 run gazebo_ros spawn_entity.py -file /mnt/d/TbbRobot/models/turtlebot3_custom/model.sdf -entity turtlebot3 -x 0 -y 0 -z 0.01
```

#### 步骤 3: 启动 Robot State Publisher

```bash
ros2 launch turtlebot3_gazebo robot_state_publisher.launch.py use_sim_time:=true &
sleep 3
```

#### 步骤 4: 启动 AMCL 定位

```bash
ros2 launch nav2_bringup localization_launch.py use_sim_time:=true map:=/mnt/d/TbbRobot/maps/power_room.yaml &
sleep 5

# 手动激活 AMCL (如果 lifecycle manager 超时)
ros2 lifecycle set /map_server activate
ros2 lifecycle set /amcl activate
```

#### 步骤 5: 启动 Nav2 导航

```bash
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true &
sleep 5
```

#### 步骤 6: 启动 Web 通信服务

```bash
# Rosbridge WebSocket (端口 9090)
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
sleep 2

# Web Video Server (端口 8080)
ros2 run web_video_server web_video_server &
sleep 2
```

#### 步骤 7: 发布初始位姿

```bash
ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped "{
  header: {frame_id: 'map'},
  pose: {
    pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}},
    covariance: [0.25, 0, 0, 0, 0, 0, 0, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0685]
  }
}"
```

#### 步骤 8: 启动 Web 控制台 (Windows PowerShell)

```powershell
cd d:\TbbRobot\web
python -m http.server 8888
```

然后在浏览器中访问: http://localhost:8888

**服务端口说明**:
| 服务 | 端口 | 说明 |
|------|------|------|
| Web 控制台 | 8888 | 静态 HTML 页面 |
| Rosbridge | 9090 | WebSocket 通信 |
| 视频流 | 8080 | web_video_server |

摄像头视频流地址: http://localhost:8080/stream?topic=/camera/image_raw

## 升降杆控制

机器人配备可升降摄像头支架，通过 ROS2 话题控制：

```bash
# 启动升降杆控制器
python3 /mnt/d/TbbRobot/scripts/lift_position_controller.py &

# 设置升降高度 (0.0 - 0.5 米)
ros2 topic pub /lift/target_position std_msgs/msg/Float64 "{data: 0.3}"
```

## 仿真环境

### 配电室 (power_room)
- 尺寸：25m x 20m
- 包含：4排配电柜、仪表盘、彩色标记
- 巡检点：各配电柜前方

## 主要话题

| 话题 | 类型 | 描述 |
|------|------|------|
| `/cmd_vel` | geometry_msgs/Twist | 速度控制 |
| `/scan` | sensor_msgs/LaserScan | 激光雷达数据 |
| `/camera/image_raw` | sensor_msgs/Image | 摄像头图像 |
| `/odom` | nav_msgs/Odometry | 里程计 |
| `/map` | nav_msgs/OccupancyGrid | 地图 |
| `/amcl_pose` | geometry_msgs/PoseWithCovarianceStamped | AMCL 定位 |
| `/lift/target_position` | std_msgs/Float64 | 升降杆目标高度 |
| `/lift/current_position` | std_msgs/Float64 | 升降杆当前高度 |

## 已知问题

### Gazebo WSLg 黑屏
在 WSL2 + WSLg 环境下，使用 Intel 集成显卡可能导致 Gazebo GUI 黑屏。

**解决方案**：使用 NVIDIA 独立显卡 (如 RTX 4060)，WSL 会自动识别并使用。

详见 [docs/gazebo_wslg_black_screen_troubleshooting.md](docs/gazebo_wslg_black_screen_troubleshooting.md)

## 依赖包

```bash
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup \
    ros-humble-turtlebot3-gazebo ros-humble-rosbridge-server \
    ros-humble-web-video-server ros-humble-gazebo-ros-pkgs
```

## 许可证

MIT License

## 参考

- [ROS2 Humble 文档](https://docs.ros.org/en/humble/)
- [Nav2 导航栈](https://docs.nav2.org/)
- [TurtleBot3](https://emanual.robotis.com/docs/en/platform/turtlebot3/)
- [Gazebo Classic](http://gazebosim.org/)
