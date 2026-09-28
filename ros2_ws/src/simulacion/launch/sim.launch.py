"""Simulación en Gazebo Harmonic: hilera de limoneros + Arturito (base con IMU y GPS, brazo y pinza).
brazo_sim hace de firmware del brazo (arranca DESARMADO) y brazo_ik resuelve /brazo/objetivo. limones_sim publica
/limon/posicion como la visión real y engancha el limón a la pinza al cerrar. Con mision:=true corre la misión.
Con vision:=yolo, /limon/posicion sale de la cadena real: cámaras de Gazebo -> disparidad -> YOLO -> localizador
(hace falta `source ~/yolo_ws/install/setup.bash`, el venv ~/yolo_env y el modelo en ~/vision_estereo/modelos).

    ros2 launch simulacion sim.launch.py              # con ventana de Gazebo
    ros2 launch simulacion sim.launch.py gui:=false   # solo el servidor (notebook lenta)
    ros2 launch simulacion sim.launch.py mision:=true # con la misión: arrimar el robot a un limón con el teleop
    ros2 launch simulacion sim.launch.py mision:=true vision:=yolo   # con cámaras y YOLO
    ros2 run teleop_twist_keyboard teleop_twist_keyboard   # mover la base (en otra terminal)
"""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, EqualsSubstitution, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = Path(get_package_share_directory('simulacion'))
    gz_launch = str(Path(get_package_share_directory('ros_gz_sim')) / 'launch' / 'gz_sim.launch.py')
    mundo = str(share / 'worlds' / 'hilera.sdf')
    gui = LaunchConfiguration('gui')
    yolo = IfCondition(EqualsSubstitution(LaunchConfiguration('vision'), 'yolo'))
    camaras = PythonExpression(["'true' if '", LaunchConfiguration('vision'), "' == 'yolo' else 'false'"])
    robot = ParameterValue(Command(['xacro ', str(share / 'urdf' / 'arturito.urdf.xacro'), ' camaras:=', camaras]),
                           value_type=str)
    # Ventana de disparidad para 0,40-0,95 m como ventana_disparidad() de limon.launch.py: f*B = 106,854 px*m
    # -> 112..268 px -> min 112, rango 160 (múltiplo de 16)
    modelo = str(Path.home() / 'vision_estereo' / 'modelos' / 'limon_yolo26n_ncnn_model')
    venv = str(Path.home() / 'yolo_env' / 'lib' / 'python3.12' / 'site-packages')
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='false = solo el servidor de Gazebo'),
        DeclareLaunchArgument('mision', default_value='false', description='true = correr la misión (arma el brazo)'),
        DeclareLaunchArgument('vision', default_value='simulada', description='simulada | yolo (cámaras + YOLO)'),
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
        Node(package='simulacion', executable='limones_sim', output='screen',
             parameters=[{'use_sim_time': True,
                          'publicar_vision': PythonExpression(["'", LaunchConfiguration('vision'), "' != 'yolo'"])}]),
        # --- vision:=yolo: la cadena de vision_estereo sobre las cámaras de Gazebo ---
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='puente_camaras', condition=yolo,
             arguments=['/left/image_rect@sensor_msgs/msg/Image[gz.msgs.Image',
                        '/right/image_rect@sensor_msgs/msg/Image[gz.msgs.Image'],
             parameters=[{'use_sim_time': True}]),
        Node(package='simulacion', executable='camara_info_sim', condition=yolo, parameters=[{'use_sim_time': True}]),
        Node(package='stereo_image_proc', executable='disparity_node', name='disparity', condition=yolo,
             parameters=[{'use_sim_time': True, 'approximate_sync': True, 'queue_size': 10, 'stereo_algorithm': 0,
                          'min_disparity': 112, 'disparity_range': 160}]),
        Node(package='yolo_ros', executable='detector_node', output='screen', condition=yolo,
             # conf 0,25 (en el robot, 0,40): el modelo se entrenó con fotos reales y a los limones de Gazebo les da
             # menos confianza. Los falsos positivos lejanos los descarta el localizador por distancia (z_max)
             parameters=[{'use_sim_time': True, 'modelo': modelo, 'imagen': '/left/image_rect',
                          'clases': ['limon'], 'conf': 0.25}],
             additional_env={'PYTHONPATH': venv + ':' + os.environ.get('PYTHONPATH', ''),
                             'OMP_WAIT_POLICY': 'PASSIVE'}),
        Node(package='yolo_ros', executable='localizador_node', output='screen', condition=yolo,
             parameters=[{'use_sim_time': True, 'z_min': 0.40, 'z_max': 0.95, 'clase': 'limon'}]),
        # La TF brazo -> cámara la da el urdf (robot_state_publisher): no se usa mision.launch.py
        # reposo = muñeca con q = (-60°, 45°, 0°), el de brazo_sim: el brazo no tapa las cámaras
        Node(package='mision', executable='nodo_mision', output='screen',
             parameters=[{'use_sim_time': True, 'reposo': [0.18416, -0.31898, 0.09103]}],
             condition=IfCondition(LaunchConfiguration('mision'))),
    ])
