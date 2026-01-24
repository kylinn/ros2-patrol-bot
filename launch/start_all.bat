@echo off
REM TbbRobot 完整巡检系统启动脚本
REM 请在 Windows 命令提示符中运行，确保已 source ROS2 环境

echo ========================================
echo TbbRobot 巡检系统启动脚本
echo ========================================

REM 检查 ROS2 环境
where ros2 >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] ros2 命令未找到，请先设置 ROS2 环境
    echo 例如: call C:\dev\ros2_humble\local_setup.bat
    pause
    exit /b 1
)

echo.
echo [提示] 本脚本将启动以下服务:
echo   1. Gazebo 仿真环境 (带 power_room 世界)
echo   2. 机器人模型 (带升降杆)
echo   3. AMCL 定位
echo   4. Nav2 导航
echo   5. rosbridge (WebSocket)
echo   6. web_video_server (视频流)
echo.
echo [提示] 请在多个终端中分别运行以下命令:
echo.

echo ========== 终端 1: Gazebo ==========
echo ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py world:=d:/TbbRobot/worlds/power_room.world
echo.

echo ========== 终端 2: 生成机器人 (等 Gazebo 完全启动后) ==========
echo ros2 run gazebo_ros spawn_entity.py -entity turtlebot3_custom -file d:/TbbRobot/models/turtlebot3_custom/model.sdf -x 0 -y 0 -z 0.01
echo.

echo ========== 终端 3: AMCL 定位 ==========
echo ros2 launch nav2_bringup localization_launch.py use_sim_time:=true map:=d:/TbbRobot/maps/power_room.yaml
echo.

echo ========== 终端 4: Nav2 导航 ==========
echo ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true
echo.

echo ========== 终端 5: rosbridge ==========
echo ros2 launch rosbridge_server rosbridge_websocket_launch.xml
echo.

echo ========== 终端 6: web_video_server ==========
echo ros2 run web_video_server web_video_server
echo.

echo ========================================
echo 启动完成后，用浏览器打开:
echo   file:///d:/TbbRobot/web/index.html
echo ========================================
echo.
pause
