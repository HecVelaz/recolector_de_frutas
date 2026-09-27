"""Nodo brazo_ik: objetivo 3D de la muñeca -> ángulos de las articulaciones (cinemática inversa de la E4).

Suscribe  /brazo/objetivo   geometry_msgs/PointStamped  [m], marco `marco` (por defecto brazo_base)
Publica   /brazo/joint_cmd  sensor_msgs/JointState      j1, j2, j3 [rad] (solo si el punto es alcanzable)
          /brazo/ik_estado  std_msgs/String             "ok ..." o "inalcanzable: <motivos>"

El firmware del brazo trabaja en grados: su capa micro-ROS convierte (REP-103: ROS usa rad).
Si el objetivo viene en otro marco, se rechaza: la transformación cámara -> brazo la hace stereo_3d.
"""

import math

from geometry_msgs.msg import PointStamped
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String

from brazo_ik.cinematica import cinematica_inversa

NOMBRES = ['j1', 'j2', 'j3']


def resolver(x_m, y_m, z_m):
    """Objetivo en metros -> (posiciones [rad] o None, texto de estado). Sin ROS: se prueba en test/."""
    soluciones, motivos = cinematica_inversa(x_m * 1000.0, y_m * 1000.0, z_m * 1000.0)
    if not soluciones:
        return None, 'inalcanzable: ' + '; '.join(motivos)
    s = soluciones[0]
    grados = ', '.join(f'{math.degrees(q):.2f}' for q in (s.q1, s.q2, s.q3))
    return [s.q1, s.q2, s.q3], f'ok q=[{grados}]° mu={math.degrees(s.mu):.1f}° err={s.err:.2e} mm'


class NodoIK(Node):

    def __init__(self):
        super().__init__('brazo_ik')
        self.marco = self.declare_parameter('marco', 'brazo_base').value
        self.pub_cmd = self.create_publisher(JointState, '/brazo/joint_cmd', 10)
        self.pub_estado = self.create_publisher(String, '/brazo/ik_estado', 10)
        self.create_subscription(PointStamped, '/brazo/objetivo', self.al_recibir, 10)
        self.get_logger().info(f'brazo_ik listo: /brazo/objetivo (marco {self.marco}) -> /brazo/joint_cmd')

    def al_recibir(self, msg):
        if msg.header.frame_id and msg.header.frame_id != self.marco:
            texto = f'inalcanzable: marco "{msg.header.frame_id}" distinto de "{self.marco}"'
            self.get_logger().warn(texto)
            self.pub_estado.publish(String(data=texto))
            return
        q, texto = resolver(msg.point.x, msg.point.y, msg.point.z)
        self.pub_estado.publish(String(data=texto))
        if q is None:
            self.get_logger().warn(texto)
            return
        cmd = JointState()
        cmd.header.stamp = self.get_clock().now().to_msg()
        cmd.header.frame_id = self.marco
        cmd.name = NOMBRES
        cmd.position = q
        self.pub_cmd.publish(cmd)
        self.get_logger().info(texto)


def main(args=None):
    rclpy.init(args=args)
    nodo = NodoIK()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
