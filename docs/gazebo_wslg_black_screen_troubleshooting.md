# Gazebo GUI 在 WSLg 下黑屏问题排查文档

## 最终解决方案

**问题已解决！** 使用 NVIDIA RTX 4060 独立显卡后，Gazebo GUI 正常显示。

WSLg 默认使用 Intel 集成显卡 (通过 D3D12 驱动)，这导致了黑屏问题。切换到 NVIDIA GPU 后问题解决。

系统自动识别到 NVIDIA 驱动:
```
NVIDIA-SMI 575.51.02    Driver Version: 576.02    CUDA Version: 12.9
NVIDIA GeForce RTX 4060 Laptop GPU
```

---

## 问题描述

在 Windows 11 + WSL2 (Ubuntu 22.04) + WSLg 环境下，运行 Gazebo Classic 11.10.2 的 gzclient (GUI客户端) 时，窗口显示为黑屏，无法渲染任何3D场景内容。

## 环境信息

### 系统环境
- **操作系统**: Windows 11
- **WSL版本**: WSL2
- **Linux发行版**: Ubuntu 22.04 (jammy)
- **图形后端**: WSLg (Windows Subsystem for Linux GUI)
- **ROS版本**: ROS2 Humble

### 软件版本
- **Gazebo**: Gazebo Classic 11.10.2
- **Mesa**: 23.2.1-1ubuntu3.1~22.04.3 (kisak-mesa PPA)
- **OGRE**: 1.9 (Gazebo 11 默认使用)

### 硬件信息
- **GPU**: Intel UHD Graphics (集成显卡)
- **Mesa Driver**: D3D12 (llvmpipe软件渲染备选)

## 症状

1. gzserver 正常启动，可以加载世界文件和机器人模型
2. gzclient 能够连接到 gzserver (日志显示 "Connected to gazebo master")
3. gzclient 窗口打开，但内容完全黑屏
4. 没有渲染任何3D场景、机器人模型或UI元素
5. 鼠标移动时无任何响应

## OGRE 日志分析

查看 `~/.gazebo/ogre.log`，关键信息：

```
OpenGL版本信息:
***************************************
*** OpenGL 3.1 Renderer Started     ***
***************************************
GL_VERSION = 4.1 (Core Profile) Mesa 23.2.1
GL_VENDOR = Microsoft Corporation
GL_RENDERER = D3D12 (Intel(R) UHD Graphics)

渲染能力:
* VBO support: VBO
* Stencil buffer depth: 8
* Hardware generation of mipmaps: yes
* Texture blending: yes
* Anisotropic filtering: yes
* Dot product texture operation: yes
* Vertex texture fetch: yes
* Number of texture units: 16
* Infinite far plane projection: yes
* Hardware render-to-texture: FBO PBuffer
* Floating point textures: yes
* Non-power-of-two textures: yes
* Volume textures: yes
* Max Texture resolution: 16384
* Max Lights: 8
* Multiple Render Targets: 8
* Max Point Size: 255
* Vertex Programs: yes
* Fragment Programs: yes
* Geometry Programs: yes
* Tessellation Hull Programs: no
* Tessellation Domain Programs: no
* Compute Programs: no
* GL GLSL: yes
* GLSL Version: 4.10
* Separate shader objects: no
* Using FSAA from GL_ARB_multisample extension

成功创建的纹理:
Texture: SkyX_Starfield.png: Loading 1 faces(PF_L8,512x512x1)
Texture: SkyX_Moon.png: Loading 1 faces(PF_A8R8G8B8,512x512x1)
Texture: SkyX_MoonHalo.png: Loading 1 faces(PF_A8R8G8B8,512x256x1)
Texture: Noise.jpg: Loading 1 faces(PF_R8G8B8,1024x1024x1)

窗口创建:
GLRenderSystem::_createRenderWindow "OgreWindow(1)", 1102x334 windowed
GLXWindow::create used FBConfigID = 355
```

## 已尝试的解决方案

### 1. 强制使用 D3D12 驱动
```bash
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME=Intel
gzclient --verbose
```
**结果**: 仍然黑屏

### 2. 强制使用软件渲染 (llvmpipe)
```bash
export LIBGL_ALWAYS_SOFTWARE=1
gzclient --verbose
```
**结果**: 仍然黑屏

### 3. 设置 OGRE RTT 模式为 Copy
```bash
export OGRE_RTT_MODE=Copy
gzclient --verbose
```
**结果**: 仍然黑屏

### 4. 覆盖 OpenGL 版本
```bash
export MESA_GL_VERSION_OVERRIDE=3.3
gzclient --verbose
```
**结果**: 仍然黑屏

### 5. 禁用 MIT-SHM
```bash
export QT_X11_NO_MITSHM=1
gzclient --verbose
```
**结果**: 仍然黑屏

### 6. 组合多种环境变量
```bash
export DISPLAY=:0
export LIBGL_ALWAYS_SOFTWARE=1
export OGRE_RTT_MODE=Copy
export MESA_GL_VERSION_OVERRIDE=3.3
export QT_X11_NO_MITSHM=1
gzclient --verbose
```
**结果**: 仍然黑屏

### 7. 更新 Mesa 驱动
```bash
# 添加 kisak-mesa PPA
sudo add-apt-repository ppa:kisak/kisak-mesa
sudo apt update
sudo apt upgrade mesa-utils
```
**结果**: Mesa 版本为 23.2.1，但仍然黑屏

### 8. 检查 Gazebo verbose 输出
```
gzclient --verbose
```
输出显示：
- 成功连接到 gazebo master
- 没有明显的错误信息
- 只有一个警告: "Warning: Deleting a connection right after creation"

## 相关参考

### GitHub Issue
- https://github.com/microsoft/wslg/issues/824

该 issue 描述了类似问题，提出的解决方案包括：
1. 使用 VcXsrv (用户不希望使用)
2. 使用 OGRE_RTT_MODE=Copy (已尝试，无效)
3. 使用软件渲染 (已尝试，无效)

## 技术分析

### 可能的根本原因

1. **WSLg + OGRE 1.9 兼容性问题**
   - Gazebo 11 使用 OGRE 1.9 渲染引擎
   - WSLg 使用 Weston compositor 和 RDP 协议
   - OGRE 的某些渲染路径可能与 WSLg 的图形栈不兼容

2. **Render-to-Texture (RTT) 问题**
   - OGRE 使用 FBO (Framebuffer Object) 进行 RTT
   - WSLg 的 Mesa D3D12 驱动可能不完全支持某些 FBO 操作

3. **GLX/EGL 上下文问题**
   - Gazebo 使用 GLX 创建 OpenGL 上下文
   - WSLg 底层可能存在 GLX 到 EGL 的转换问题

4. **帧缓冲显示问题**
   - 渲染可能正常完成，但最终帧无法正确显示到窗口
   - 可能是 swapbuffers 或 compositor 层面的问题

## 待尝试的方案

### 1. 使用 Gazebo Sim (Ignition) 替代
```bash
sudo apt install ros-humble-ros-gz
ros2 launch ros_gz_sim gz_sim.launch.py gz_args:="-r empty.sdf"
```
Ignition/Gazebo Sim 使用 OGRE 2.x，可能有更好的兼容性。

### 2. 使用 X11 forwarding + VcXsrv
如果必须使用原生 X11：
```bash
# Windows 端安装 VcXsrv
# 启动 XLaunch，选择 "Multiple windows"，勾选 "Disable access control"
export DISPLAY=<windows_ip>:0.0
gzclient
```

### 3. 使用远程桌面连接到 WSL
通过 xrdp 服务：
```bash
sudo apt install xrdp xfce4
sudo systemctl start xrdp
# 然后用 Windows 远程桌面连接到 localhost:3390
```

### 4. 尝试 EGL 后端 (如果 Gazebo 支持)
```bash
export GAZEBO_GUI_RENDER_SYSTEM=OGRE_EGL
gzclient
```

### 5. 降级到 OGRE 1.8 或尝试不同的渲染路径
需要重新编译 Gazebo。

### 6. 检查 weston log
```bash
cat /mnt/wslg/runtime-dir/wayland-0.log
# 或
journalctl --user -u weston
```

### 7. 使用 headless 模式 + Web 可视化
放弃 gzclient，使用 gzweb 或其他 Web 可视化方案：
```bash
# 安装 gzweb
cd ~
git clone https://github.com/osrf/gzweb
cd gzweb
./deploy.sh -m local
# 启动
npm start
# 访问 http://localhost:8080
```

## 当前工作状态

尽管 Gazebo GUI 无法正常显示，以下服务仍然正常工作：

1. **gzserver**: 仿真服务器正常运行
2. **机器人模型**: 已成功生成 (spawn)
3. **ROS2 话题**: 所有话题正常发布
4. **摄像头**: `/camera/image_raw` 正常发布图像 (~2Hz)
5. **AMCL**: 定位服务正常
6. **Nav2**: 导航服务正常
7. **rosbridge**: WebSocket 桥接正常
8. **web_video_server**: 视频流服务正常

可以通过 Web 界面 (http://localhost:8088) 进行机器人控制和巡检，只是无法使用 Gazebo 原生 GUI 进行场景可视化。

## 文件位置

- OGRE 日志: `~/.gazebo/ogre.log`
- Gazebo 日志: `~/.gazebo/log/`
- gzclient 启动脚本: `/tmp/start_gzclient.sh`

## 创建日期
2026-01-24
