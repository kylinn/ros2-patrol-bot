cmake_minimum_required(VERSION 3.8)
project(patrol_robot_core)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

# Install Python modules
ament_python_install_package(${PROJECT_NAME})

# Install Python executables
install(PROGRAMS
  patrol_robot_core/patrol_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME patrol_node
)

install(PROGRAMS
  patrol_robot_core/audio_player_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME audio_player_node
)

install(PROGRAMS
  patrol_robot_core/simple_patrol.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME simple_patrol
)

install(PROGRAMS
  patrol_robot_core/auto_mapping_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME auto_mapping
)

install(PROGRAMS
  patrol_robot_core/waypoint_mapper.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME waypoint_mapper
)

install(PROGRAMS
  patrol_robot_core/simple_mapping.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME simple_mapping
)

install(PROGRAMS
  patrol_robot_core/smart_explorer.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME smart_explorer
)

# Install launch files
install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

# Install config files
install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
)

ament_package()
