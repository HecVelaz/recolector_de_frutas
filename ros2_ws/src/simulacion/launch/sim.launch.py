"""Simulación en Gazebo Harmonic: hilera de limoneros + Arturito (base con IMU y GPS, brazo y pinza).
brazo_sim hace de firmware del brazo (arranca DESARMADO) y brazo_ik resuelve /brazo/objetivo.

    ros2 launch simulacion sim.launch.py              # con ventana de Gazebo
    ros2 launch simulacion sim.launch.py gui:=false   # solo el servidor (notebook lenta)
    ros2 run teleop_twist_keyboard teleop_twist_keyboard   # mover la base (en otra terminal)
"""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = Path(get_package_share_directory('simulacion'))
    gz_launch = str(Path(get_package_share_directory('ros_gz_sim')) / 'launch' / 'gz_sim.launch.py')
    mundo = str(share / 'worlds' / 'hilera.sdf')
    gui = LaunchConfiguration('gui')
    robot = ParameterValue(Command(['xacro ', str(share / 'urdf' / 'arturito.urdf.xacro')]), value_type=str)
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='false = solo el servidor de Gazebo'),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', str(share / 'models')),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gz_launch),
                                 launch_arguments={'gz_args': f'-r {mundo}'}.items(), condition=IfCondition(gui)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gz_launch),
                                 launch_arguments={'gz_args': f'-r -s --headless-rendering {mundo}'}.items(),
                                 condition=UnlessCondition(gui)),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot, 'use_sim_time': True}]),
        Node(package='ros_gz_sim', executable='create', output='screen',
             arguments=['-topic', 'robot_description', '-name', 'arturito', '-z', '0.06']),
        Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
             parameters=[{'config_file': str(share / 'config' / 'puente.yaml'), 'use_sim_time': True}]),
        Node(package='simulacion', executable='brazo_sim', output='screen', parameters=[{'use_sim_time': True}]),
        Node(package='brazo_ik', executable='nodo_ik', output='screen', parameters=[{'use_sim_time': True}]),
    ])
