"""Misión mínima: TF brazo -> cámaras + brazo_ik + mision. La visión (vision_estereo, limon.launch.py) y los agentes
micro-ROS se lanzan aparte.

TF: brazo_base -> stereo_camera_link (x adelante, y a la izquierda, z arriba, en el centro de la cámara izquierda).
limon.launch.py publica stereo_camera_link -> camera (marco óptico) y /limon/posicion viene en `camera`.
Sin valores por defecto a propósito: con una TF inventada el brazo iría a un punto equivocado pero alcanzable.
Medirla con el soporte rígido y pasarla entera (roll, pitch, yaw en rad), p. ej.
    ros2 launch mision mision.launch.py x:=-0.10 y:=0 z:=0.35 roll:=0 pitch:=0 yaw:=0
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Posición [m] y orientación [rad] de la cámara izquierda respecto de brazo_base (MEDIR)
TF_CAMARA = ('x', 'y', 'z', 'roll', 'pitch', 'yaw')


def generate_launch_description():
    tf_args = []
    for k in TF_CAMARA:
        tf_args += [f'--{k}', LaunchConfiguration(k)]
    return LaunchDescription(
        [DeclareLaunchArgument(k, description='TF brazo_base -> stereo_camera_link (MEDIR)') for k in TF_CAMARA] + [
            Node(package='tf2_ros', executable='static_transform_publisher', name='brazo_camara_tf',
                 arguments=tf_args + ['--frame-id', 'brazo_base', '--child-frame-id', 'stereo_camera_link']),
            Node(package='brazo_ik', executable='nodo_ik', name='brazo_ik', output='screen'),
            Node(package='mision', executable='nodo_mision', name='mision', output='screen'),
        ])
