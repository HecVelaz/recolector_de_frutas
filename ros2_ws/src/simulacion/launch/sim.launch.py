"""Simulación en Gazebo Harmonic: hilera de limoneros + Arturito (base con IMU y GPS, brazo y pinza).
brazo_sim hace de firmware del brazo (arranca DESARMADO) y brazo_ik resuelve /brazo/objetivo. limones_sim publica
/limon/posicion como la visión real y engancha el limón a la pinza al cerrar. Con mision:=true corre la misión.
Con vision:=yolo, /limon/posicion sale de la cadena real: cámaras de Gazebo -> disparidad -> YOLO -> localizador
(hace falta `source ~/yolo_ws/install/setup.bash`, el venv ~/yolo_env y el modelo en ~/vision_estereo/modelos).

    ros2 launch simulacion sim.launch.py              # con ventana de Gazebo
    ros2 launch simulacion sim.launch.py gui:=false   # solo el servidor (notebook lenta)
    ros2 launch simulacion sim.launch.py mision:=true # con la misión: arrimar el robot a un limón con el teleop
    ros2 launch simulacion sim.launch.py mision:=true autonomo:=true   # recorre la hilera y cosecha sola
    ros2 launch simulacion sim.launch.py mision:=true vision:=yolo   # con cámaras y YOLO
    ros2 launch simulacion sim.launch.py mundo:=arbolitos mision:=true   # demo: banderín + hilera de arbolitos
    ros2 launch simulacion sim.launch.py mundo:=arbolitos mision:=true arboles:=2 lados:=1 separacion:=1.5 \
        pose:=-2.0,0.5,17 gui:=false     # pose inicial x, y [m], rumbo [°] (el banderín está en el origen)
mundo:=arbolitos genera el mundo (mundo_arbolitos.py) y la hilera (JSON para la navegación) con arboles y separacion,
usa la cámara de navegación del mástil (camara:=nav del urdf) y el detector del banderín (nodo_banderin) y, con
mision:=true, la misión navega con el banderín (navegacion.py) y registro_nav guarda resultados/nav_<fecha>.csv.
    ros2 topic pub --once /base/comando std_msgs/msg/String "{data: armar}"   # base_sim arranca DESARMADA
    ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p repeat_rate:=10.0   # mover la base
    (repeat_rate: base_sim frena si /cmd_vel no llega en 300 ms, como la S3 con micro-ROS)
En cada terminal que hable con la simulación: export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST (si no, no la ve y, peor,
puede hablar con los ESP32 reales de la Pi por la red).
"""

import json
import math
import os
from pathlib import Path
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription,
                            OpaqueFunction, SetEnvironmentVariable)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, EqualsSubstitution, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


# Cámara de navegación del mástil (camara:=nav): f y -f·B de vision_estereo/config/calibracion_mastil; zona con
# disparidad u >= 280 px (26-sim-alcance-arbolito)
F_NAV, TX_NAV, U_MIN_NAV = 672.126313, -67.432454, 280.0


def arbolitos(arboles, separacion):
    """Genera el mundo y la hilera (JSON) en una carpeta temporal -> (mundo.sdf, hilera.json)."""
    from mision.navegacion import hilera_recta
    from simulacion.mundo_arbolitos import generar
    hilera = hilera_recta(arboles, separacion)
    carpeta = Path(tempfile.mkdtemp(prefix='arbolitos_'))
    (carpeta / 'arbolitos.sdf').write_text(generar(hilera, f'{arboles} árboles cada {separacion} m'))
    (carpeta / 'hilera.json').write_text(json.dumps(hilera, indent=2))
    return str(carpeta / 'arbolitos.sdf'), str(carpeta / 'hilera.json')


def armar(context):
    share = Path(get_package_share_directory('simulacion'))
    gz_launch = str(Path(get_package_share_directory('ros_gz_sim')) / 'launch' / 'gz_sim.launch.py')
    valor = lambda nombre: LaunchConfiguration(nombre).perform(context)  # noqa: E731
    demo = valor('mundo') == 'arbolitos'
    if demo:
        mundo, hilera = arbolitos(int(valor('arboles')), float(valor('separacion')))
    else:
        mundo = str(share / 'worlds' / f'{valor("mundo")}.sdf')
    x, y, rumbo = (float(v) for v in valor('pose').split(','))
    gui = LaunchConfiguration('gui')
    yolo = IfCondition(EqualsSubstitution(LaunchConfiguration('vision'), 'yolo'))
    camaras = 'true' if demo or valor('vision') == 'yolo' else 'false'
    robot = ParameterValue(Command(['xacro ', str(share / 'urdf' / 'arturito.urdf.xacro'), ' camaras:=', camaras,
                                    ' camara:=', 'nav' if demo else 'v1']), value_type=str)
    camara = {'f': F_NAV, 'tx': TX_NAV} if demo else {}
    # Reposo del brazo (TCP en brazo_base, q = (75°, 94°, -50°)); en la demo con J1 = 0°: a 75° la pinza tapa la
    # cámara de navegación (el real espera plegado sobre la canasta, J1 = 130°, fuera del límite de J1 de la sim)
    reposo = [0.29287, 0.0, 0.27605] if demo else [0.07580, 0.28289, 0.27605]
    con_mision = IfCondition(LaunchConfiguration('mision'))
    navegacion = {'navegacion': True, 'hilera': hilera, 'lados': int(valor('lados'))} if demo else {}
    # Ventana de disparidad para 0,40-0,95 m como ventana_disparidad() de limon.launch.py: f*B = 106,854 px*m
    # -> 112..268 px -> min 112, rango 160 (múltiplo de 16)
    modelo = str(Path.home() / 'vision_estereo' / 'modelos' / 'limon_yolo26n_ncnn_model')
    venv = str(Path.home() / 'yolo_env' / 'lib' / 'python3.12' / 'site-packages')
    demo_nodos = [
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='puente_camara_izq',
             arguments=['/left/image_rect@sensor_msgs/msg/Image[gz.msgs.Image'], parameters=[{'use_sim_time': True}]),
        Node(package='simulacion', executable='camara_info_sim', parameters=[{'use_sim_time': True, **camara}]),
        Node(package='mision', executable='nodo_banderin', output='screen', parameters=[{'use_sim_time': True}]),
        Node(package='simulacion', executable='registro_nav', output='screen', condition=con_mision,
             parameters=[{'use_sim_time': True, 'mundo': mundo,
                          'nota': f'pose {valor("pose")}, lados {valor("lados")}, separacion {valor("separacion")}'}]),
    ] if demo else []
    return [
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gz_launch),
                                 launch_arguments={'gz_args': f'-r {mundo}'}.items(), condition=IfCondition(gui)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gz_launch),
                                 launch_arguments={'gz_args': f'-r -s --headless-rendering {mundo}'}.items(),
                                 condition=UnlessCondition(gui)),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot, 'use_sim_time': True}]),
        Node(package='ros_gz_sim', executable='create', output='screen',
             arguments=['-topic', 'robot_description', '-name', 'arturito', '-z', '0.08', '-x', str(x), '-y', str(y),
                        '-Y', str(math.radians(rumbo))]),
        Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
             parameters=[{'config_file': str(share / 'config' / 'puente.yaml'), 'use_sim_time': True}]),
        Node(package='simulacion', executable='brazo_sim', output='screen',
             parameters=[{'use_sim_time': True, **({'reposo_j1': 0.0} if demo else {})}]),
        # Seguridad de la base como la S3: arranca DESARMADA ('armar' por /base/comando) y frena si /cmd_vel no
        # llega en 300 ms (teleop con repeat_rate)
        Node(package='simulacion', executable='base_sim', output='screen', parameters=[{'use_sim_time': True}]),
        # Herramienta horizontal (uArm): /brazo/objetivo es el punto de agarre, a 0,075 m de la muñeca (urdf: largo_tcp)
        Node(package='brazo_ik', executable='nodo_ik', output='screen',
             parameters=[{'use_sim_time': True, 'largo_herramienta': 0.075}]),
        Node(package='simulacion', executable='limones_sim', output='screen',
             parameters=[{'use_sim_time': True, 'mundo': mundo,
                          **({'f': F_NAV, 'u_min': U_MIN_NAV} if demo else {}),
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
        # reposo = TCP con q = (75°, 94°, -50°) (provisorio, ver fsm.py), el de brazo_sim (el brazo no tapa las cámaras ni toca el mástil):
        # muñeca + 0,075 m en la dirección de J1. cierre 40 %: los dedos quedan sobre el limón (Ø 56 mm)
        Node(package='mision', executable='nodo_mision', output='screen',
             parameters=[{'use_sim_time': True, 'reposo': reposo, 'largo_herramienta': 0.075,
                          'cierre': 40.0, 'autonomo': ParameterValue(LaunchConfiguration('autonomo'), value_type=bool),
                          **navegacion}],
             condition=con_mision),
    ] + demo_nodos


def generate_launch_description():
    share = Path(get_package_share_directory('simulacion'))
    return LaunchDescription([
        # AISLAMIENTO: la simulación no sale de esta máquina. Sin esto, ROS 2 descubre por la red los ESP32 reales
        # (conectados a la Pi): la misión simulada leía el /brazo/estado del brazo real y le mandaba comandos.
        # Las terminales del teleop y de los `ros2 topic` necesitan lo mismo: export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
        SetEnvironmentVariable('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST'),
        SetEnvironmentVariable('GZ_IP', '127.0.0.1'),
        DeclareLaunchArgument('gui', default_value='true', description='false = solo el servidor de Gazebo'),
        DeclareLaunchArgument('mision', default_value='false', description='true = correr la misión (arma el brazo)'),
        DeclareLaunchArgument('autonomo', default_value='false',
                              description='true (con mision:=true) = recorre la hilera sola: avanza, se arrima, esquiva'),
        DeclareLaunchArgument('vision', default_value='simulada', description='simulada | yolo (cámaras + YOLO)'),
        DeclareLaunchArgument('mundo', default_value='hilera', description='hilera | arbolitos (demo con el banderín)'),
        DeclareLaunchArgument('arboles', default_value='3', description='arbolitos: cantidad de árboles (2 o 3)'),
        DeclareLaunchArgument('lados', default_value='2', description='arbolitos: 1 = solo ida, 2 = ida y vuelta'),
        DeclareLaunchArgument('separacion', default_value='1.5', description='arbolitos: m entre árboles'),
        DeclareLaunchArgument('pose', default_value='0,0,0', description='pose inicial: x,y [m],rumbo [°]'),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', str(share / 'models')),
        OpaqueFunction(function=armar),
    ])
