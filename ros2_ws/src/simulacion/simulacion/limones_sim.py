"""Nodo limones_sim: la "visión" y el agarre de los limones cosechables en Gazebo.

Visión: publica /limon/posicion (geometry_msgs/PointStamped) como el localizador_node real: marco `camera` (óptico
de la cámara izquierda), superficie del limón visible y hora de la "imagen", ~3 Hz. Solo los limones que la cadena
real podría localizar: dentro de la imagen (640x480, f = 1076,5 px, calibración v1), a 0,40-0,95 m y con u >= 271 px
(más a la izquierda el BM no tiene disparidad: min 112 + rango 160); el más cercano. Así `mision` corre igual que con
las cámaras reales.

Agarre: cuando los dedos cierran (/joint_states) con el punto de agarre (`tcp`, entre los dedos) a menos de
`dist_agarre` del centro de un limón, lo toma: mientras está agarrado lo pone en el TCP 30 veces por segundo
(servicio set_pose de Gazebo). Cuando abren, lo deja donde está y lo da por cosechado (no se vuelve a "ver"). Antes se
usaba un DetachableJoint, pero con las articulaciones movidas por velocidad la unión quedaba blanda y el limón se
atrasaba hasta 26 cm al girar J1.

Las posiciones de los limones salen del mundo (no se mueven hasta que se agarran) y la del robot, de `odom`: la base
arranca en el origen del mundo, así que odom = mundo salvo patinamiento.
"""

import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from geometry_msgs.msg import PointStamped
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState
import tf2_geometry_msgs  # noqa: F401  (registra PointStamped en tf2)
from tf2_ros import Buffer, TransformException, TransformListener


def leer_limones(archivo):
    """Modelos limon_N del mundo -> {N: (x, y, z)} [m] (los limon_fijo_* no cuentan)."""
    limones = {}
    for m in ET.parse(archivo).getroot().iter('model'):
        nombre = m.get('name', '')
        if nombre.startswith('limon_') and nombre[6:].isdigit():
            limones[int(nombre[6:])] = tuple(float(v) for v in m.find('pose').text.split()[:3])
    return limones


F, CX, CY, ANCHO, ALTO = 1076.537901, 320.0, 240.0, 640, 480  # como camara_info_sim
U_MIN = 271  # min_disparity + disparity_range - 1 del disparity_node: a la izquierda de esto no hay disparidad


def visible(p, z_min, z_max, u_min=U_MIN):
    """Punto en el marco óptico (x derecha, y abajo, z adelante): ¿lo podría localizar el estéreo?"""
    x, y, z = p
    if not z_min <= z <= z_max:
        return False
    u, v = CX + F * x / z, CY + F * y / z
    return u_min <= u < ANCHO and 0 <= v < ALTO


def superficie(p, radio):
    """Centro -> superficie visible desde la cámara (lo que da el estéreo), acercándolo `radio` sobre el rayo."""
    d = math.sqrt(sum(c * c for c in p))
    return tuple(c * (1.0 - radio / d) for c in p)


class GazeboPoses:
    """Mueve modelos con el servicio set_pose de Gazebo (bindings de Python de gz-transport, vienen con Jazzy)."""

    def __init__(self):
        for vendor in ('gz_transport_vendor', 'gz_msgs_vendor'):
            ruta = str(Path(get_package_prefix(vendor)) / 'opt' / vendor / 'lib' / 'python')
            if ruta not in sys.path:
                sys.path.append(ruta)
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.pose_pb2 import Pose
        from gz.transport13 import Node as NodoGz
        self.Boolean, self.Pose, self.nodo = Boolean, Pose, NodoGz()

    def mover(self, nombre, p):
        pedido = self.Pose(name=nombre)
        pedido.position.x, pedido.position.y, pedido.position.z = p
        pedido.orientation.w = 1.0
        return self.nodo.request('/world/hilera/set_pose', pedido, self.Pose, self.Boolean, 100)[0]


class LimonesSim(Node):

    def __init__(self):
        super().__init__('limones_sim')
        mundo = str(Path(get_package_share_directory('simulacion')) / 'worlds' / 'hilera.sdf')
        self.limones = leer_limones(self.declare_parameter('mundo', mundo).value)
        self.radio = self.declare_parameter('radio_limon', 0.03).value
        self.z_min = self.declare_parameter('z_min', 0.40).value
        self.z_max = self.declare_parameter('z_max', 0.95).value
        self.dist_agarre = self.declare_parameter('dist_agarre', 0.03).value  # m, TCP -> centro del limón
        # false: /limon/posicion lo da la cadena real (cámaras de Gazebo + YOLO); acá queda solo el agarre
        self.publicar_vision = self.declare_parameter('publicar_vision', True).value
        self.enganchado = None
        self.cosechados = set()
        self.gz = GazeboPoses()

        self.tf = Buffer()
        self.tf_listener = TransformListener(self.tf, self)
        self.pub_pos = self.create_publisher(PointStamped, '/limon/posicion', 10)
        self.create_subscription(JointState, '/joint_states', self.al_joints, 10)
        self.create_timer(1.0 / 3.0, self.ver)
        self.create_timer(1.0 / 30.0, self.llevar)
        self.get_logger().info(f'limones_sim: {len(self.limones)} limones cosechables')

    def en_marco(self, p, marco):
        """Punto (x, y, z) en odom -> marco del robot, o None sin TF."""
        msg = PointStamped()
        msg.header.frame_id = 'odom'
        msg.point.x, msg.point.y, msg.point.z = p
        try:
            q = self.tf.transform(msg, marco)
        except TransformException:
            return None
        return (q.point.x, q.point.y, q.point.z)

    def ver(self):
        ahora = self.get_clock().now()
        if not self.publicar_vision:
            return
        vistos = []
        for n, p in self.limones.items():
            if n == self.enganchado or n in self.cosechados:
                continue
            c = self.en_marco(p, 'camera')
            if c is not None and visible(c, self.z_min, self.z_max):
                vistos.append(c)
        if vistos:
            s = superficie(min(vistos, key=lambda c: c[2]), self.radio)
            msg = PointStamped()
            msg.header.stamp = ahora.to_msg()
            msg.header.frame_id = 'camera'
            msg.point.x, msg.point.y, msg.point.z = s
            self.pub_pos.publish(msg)

    def tcp(self):
        try:
            t = self.tf.lookup_transform('odom', 'tcp', Time()).transform.translation
        except TransformException:
            return None
        return (t.x, t.y, t.z)

    def llevar(self):
        """Mientras está agarrado, el limón va en el TCP."""
        if self.enganchado is not None and (p := self.tcp()) is not None:
            self.gz.mover(f'limon_{self.enganchado}', p)

    def al_joints(self, m):
        d = dict(zip(m.name, m.position))
        if 'dedo_izq_joint' not in d or 'dedo_der_joint' not in d:
            return
        apertura = (d['dedo_izq_joint'] + d['dedo_der_joint']) / 2
        # Abierta: 0,045 por dedo; sobre un limón (Ø 56 mm) cierra hasta ~0,027 (cierre 40 %)
        if self.enganchado is None and apertura < 0.03:
            if (t := self.tcp()) is None:
                return
            for n, p in self.limones.items():
                if n not in self.cosechados and math.dist(t, p) <= self.dist_agarre:
                    self.enganchado = n
                    self.get_logger().info(f'limon_{n} agarrado (TCP a {math.dist(t, p) * 100:.1f} cm)')
                    break
        elif self.enganchado is not None and apertura > 0.035:
            self.get_logger().info(f'limon_{self.enganchado} soltado: cosechado')
            self.cosechados.add(self.enganchado)
            self.enganchado = None


def main(args=None):
    rclpy.init(args=args)
    nodo = LimonesSim()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
