# TbbRobot 巡检机器人硬件设计方案

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      巡检机器人系统架构                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                        📷 摄像头+云台                         │
│                             │                               │
│                      ┌──────┴──────┐                        │
│                      │   伸缩杆     │                        │
│                      │  (0.5-2m)   │                        │
│                      └──────┬──────┘                        │
│                             │                               │
│         ┌───────────────────┼───────────────────┐           │
│         │                设备舱                  │           │
│         │  ┌──────────┐      ┌──────────┐      │           │
│         │  │ 算丰 SE9  │ ←──→ │  Jetson  │      │           │
│         │  │ 视觉AI   │ 网线  │ ROS2主控 │      │           │
│         │  └────┬─────┘      └────┬─────┘      │           │
│         │       │                  │            │           │
│         │       ▼                  ▼            │           │
│         │  ┌─────────┐      ┌───────────┐      │           │
│         │  │ 摄像头   │      │  LiDAR    │      │           │
│         │  │ 云台控制 │      │  底盘驱动  │      │           │
│         │  └─────────┘      │  Web服务   │      │           │
│         │                   └───────────┘      │           │
│         │  ┌────────────────────────────┐      │           │
│         │  │         电池 24V           │      │           │
│         │  └────────────────────────────┘      │           │
│         └───────────────────┬───────────────────┘           │
│                             │                               │
│                    ─────────┴─────────                      │
│                       底盘 TRACER                           │
└─────────────────────────────────────────────────────────────┘
```

## 2. 职责分工

| 设备 | 职责 | 通信接口 |
|------|------|---------|
| **Jetson Orin Nano** | ROS2导航、SLAM、底盘控制、Web界面、rosbridge | CAN(底盘)、USB(LiDAR)、ETH(SE9) |
| **算丰 SE9** | 视觉AI推理、YOLO检测、表计识别、缺陷检测 | USB(摄像头)、ETH(Jetson)、PWM(云台) |
| **TRACER底盘** | 电机驱动、里程计 | CAN总线 |

## 3. 硬件清单

### 3.1 导航主控
| 组件 | 型号 | 数量 | 价格(元) | 备注 |
|------|------|------|---------|------|
| 主控板 | Jetson Orin Nano 8GB | 1 | 3,000 | 含载板 |
| 激光雷达 | 思岚 RPLIDAR A2 | 1 | 1,500 | 12m量程 |

### 3.2 视觉系统
| 组件 | 型号 | 数量 | 价格(元) | 备注 |
|------|------|------|---------|------|
| AI算法盒 | 算丰 SE9 (BM1688) | 1 | 已有 | 8 TOPS |
| 云台 | 2轴云台 | 1 | 1,500 | 支持PWM/串口控制 |
| 可见光相机 | 工业USB相机 1080P | 1 | 800 | 用于巡检 |
| 红外热成像 | (可选) | 1 | 5,000+ | 测温需求 |

### 3.3 底盘
| 组件 | 型号 | 数量 | 价格(元) | 备注 |
|------|------|------|---------|------|
| 移动底盘 | 松灵 TRACER | 1 | 8,000 | 差速驱动，承重30kg |

### 3.4 结构件
| 组件 | 型号 | 数量 | 价格(元) | 备注 |
|------|------|------|---------|------|
| 升降杆 | 电动升降杆 12V | 1 | 1,000 | 行程0.5-1.5m |
| 设备架 | 2020铝型材 | 若干 | 500 | 自己组装 |

### 3.5 电源系统
| 组件 | 型号 | 数量 | 价格(元) | 备注 |
|------|------|------|---------|------|
| 电池 | 24V 20Ah 锂电池 | 1 | 1,200 | 续航约4-6小时 |
| DC-DC | 24V转19V (Jetson) | 1 | 50 | 5A |
| DC-DC | 24V转12V (SE9/云台) | 1 | 50 | 5A |
| DC-DC | 24V转5V (LiDAR/路由) | 1 | 30 | 3A |
| 配电板 | 定制 | 1 | 150 | 含保险丝、开关 |

### 3.6 其他
| 组件 | 型号 | 数量 | 价格(元) | 备注 |
|------|------|------|---------|------|
| 交换机 | 5口千兆 | 1 | 100 | 内部通信 |
| 4G模块 | (可选) | 1 | 200 | 远程访问 |
| 线材接头 | 航空插头等 | 若干 | 200 | - |

### 3.7 成本汇总
```
导航主控:     ¥4,500
视觉系统:     ¥2,300 (不含SE9)
底盘:        ¥8,000
结构件:      ¥1,500
电源系统:    ¥1,480
其他:        ¥500
─────────────────────
硬件总计:    ¥18,280 (不含SE9和红外)
```

## 4. 供电设计

```
24V 锂电池 (20Ah)
       │
       ├──→ 底盘 TRACER (24V 直接供电)
       │
       ├──→ DC-DC 24V→19V ──→ Jetson Orin Nano
       │
       ├──→ DC-DC 24V→12V ──→ 算丰 SE9
       │                  └──→ 云台
       │                  └──→ 升降杆
       │
       └──→ DC-DC 24V→5V  ──→ RPLIDAR
                          └──→ 交换机
                          └──→ 路由器
```

### 功耗估算
| 设备 | 功耗 | 电压 |
|------|------|------|
| TRACER底盘 | ~50W (平均) | 24V |
| Jetson Orin Nano | ~15W | 19V |
| 算丰 SE9 | ~15W | 12V |
| RPLIDAR A2 | ~2W | 5V |
| 云台 | ~5W | 12V |
| 其他 | ~5W | - |
| **总计** | **~92W** | - |

**续航估算**: 24V × 20Ah = 480Wh ÷ 92W ≈ **5小时**

## 5. 网络拓扑

```
                    ┌─────────────┐
                    │  交换机/路由  │
                    │ 192.168.1.1 │
                    └──────┬──────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
   ┌───────┐          ┌───────┐          ┌───────┐
   │Jetson │          │  SE9  │          │ 调试PC │
   │  .10  │          │  .20  │          │ (DHCP) │
   └───────┘          └───────┘          └───────┘

ROS2 通信使用 DDS (Fast-DDS)
所有设备在同一子网，自动发现
```

### 网络配置
```bash
# Jetson 静态IP
sudo nmcli con mod "Wired connection 1" ipv4.addresses 192.168.1.10/24
sudo nmcli con mod "Wired connection 1" ipv4.method manual

# SE9 静态IP
sudo nmcli con mod "Wired connection 1" ipv4.addresses 192.168.1.20/24
sudo nmcli con mod "Wired connection 1" ipv4.method manual
```

## 6. 软件架构

### 6.1 Jetson (ROS2 主控)
```
ros2_ws/
├── src/
│   ├── tbb_bringup/        # 启动文件
│   ├── tbb_navigation/     # 导航配置
│   ├── tbb_description/    # URDF模型
│   ├── tracer_ros2/        # 底盘驱动
│   └── tbb_web/            # Web控制界面
├── maps/                   # 地图文件
└── config/                 # 配置文件
```

### 6.2 算丰 SE9 (视觉AI)
```
vision_ws/
├── src/
│   ├── vision_detection/   # YOLO检测节点
│   ├── vision_msgs/        # 自定义消息
│   └── camera_driver/      # 摄像头驱动
└── models/                 # AI模型文件
```

### 6.3 ROS2 话题设计

| 话题 | 类型 | 发布者 | 说明 |
|------|------|--------|------|
| `/scan` | LaserScan | Jetson | 激光雷达数据 |
| `/odom` | Odometry | Jetson | 里程计 |
| `/cmd_vel` | Twist | Jetson | 速度控制 |
| `/map` | OccupancyGrid | Jetson | 地图 |
| `/camera/image_raw` | Image | SE9 | 摄像头图像 |
| `/detection/result` | DetectionArray | SE9 | AI检测结果 |
| `/gimbal/cmd` | GimbalCmd | Jetson | 云台控制 |

## 7. 通信接口

### 7.1 Jetson ↔ SE9 (ROS2 DDS)

SE9 发布检测结果：
```python
# SE9 上运行
import rclpy
from vision_msgs.msg import Detection2DArray

class DetectionPublisher(Node):
    def __init__(self):
        super().__init__('detection_publisher')
        self.publisher = self.create_publisher(
            Detection2DArray,
            '/detection/result',
            10
        )
```

Jetson 订阅检测结果：
```python
# Jetson 上运行
from vision_msgs.msg import Detection2DArray

class DetectionSubscriber(Node):
    def __init__(self):
        super().__init__('detection_subscriber')
        self.subscription = self.create_subscription(
            Detection2DArray,
            '/detection/result',
            self.detection_callback,
            10
        )

    def detection_callback(self, msg):
        for detection in msg.detections:
            self.get_logger().info(f'Detected: {detection.results[0].id}')
```

### 7.2 Jetson ↔ 底盘 (CAN)

使用 tracer_ros2 驱动包：
```bash
# 启动底盘驱动
ros2 launch tracer_bringup tracer_robot_base.launch.py
```

### 7.3 Web 控制 (rosbridge)

```bash
# Jetson 上启动
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
ros2 run web_video_server web_video_server
```

## 8. 启动流程

### 8.1 开机自启动顺序
```
1. 底盘上电
2. Jetson 上电 → 自动启动 ROS2 导航
3. SE9 上电 → 自动启动视觉检测
4. 等待30秒系统稳定
5. Web界面可访问
```

### 8.2 启动脚本
```bash
#!/bin/bash
# /home/user/start_robot.sh

# 设置环境
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0

# 启动底盘驱动
ros2 launch tracer_bringup tracer_robot_base.launch.py &

sleep 5

# 启动导航
ros2 launch tbb_navigation navigation.launch.py &

# 启动Web服务
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
ros2 run web_video_server web_video_server &

echo "Robot started!"
```

## 9. 接口定义

### 9.1 电气接口
| 接口 | 连接 | 线缆 |
|------|------|------|
| Jetson ETH | 交换机 | RJ45 |
| Jetson USB | RPLIDAR | USB-A |
| SE9 ETH | 交换机 | RJ45 |
| SE9 USB | 摄像头 | USB-A |
| 底盘 CAN | Jetson CAN | DB9/航空插头 |
| 云台 | SE9 GPIO/串口 | 杜邦线 |

### 9.2 机械接口
| 位置 | 安装方式 |
|------|---------|
| LiDAR | 顶部中心，螺丝固定 |
| 摄像头 | 云台上，螺丝固定 |
| 云台 | 升降杆顶部，法兰连接 |
| 升降杆 | 设备架顶部，螺栓固定 |
| SE9 | 设备架内，导轨安装 |
| Jetson | 设备架内，导轨安装 |
| 电池 | 底盘上/设备架底部 |

## 10. 采购清单

### 淘宝搜索关键词
```
底盘:      "松灵 TRACER ROS"
激光雷达:   "思岚 RPLIDAR A2"
主控:      "Jetson Orin Nano 8GB 开发套件"
云台:      "2轴云台 PWM 舵机"
摄像头:    "工业USB相机 1080P 广角"
升降杆:    "电动升降杆 12V 行程1米"
铝型材:    "2020铝型材 切割"
电池:      "24V 20Ah 锂电池 带保护板"
DC-DC:    "24V转12V DCDC降压模块 5A"
交换机:    "5口千兆交换机"
```

### 官方渠道
- 松灵底盘: https://www.agilex.ai
- 思岚雷达: https://www.slamtec.com
- Jetson: https://developer.nvidia.com

## 11. 后续扩展

### 11.1 可选升级
- [ ] 3D LiDAR (更好的避障)
- [ ] 红外热成像 (测温功能)
- [ ] UWB定位 (室内精确定位)
- [ ] 自动充电桩

### 11.2 软件功能扩展
- [ ] 定点巡检任务
- [ ] 异常告警推送
- [ ] 历史数据分析
- [ ] 多机器人调度

---

*文档版本: v1.0*
*更新日期: 2026-01-24*
